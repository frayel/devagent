"""Maré do mercado: índice de otimismo de 0 a 100 (spec 027).

Três componentes, todos de 0 a 100 com 100 no lado otimista:

- **Fluxo** (40%): parcela do volume financeiro do dia que foi para ações em
  alta. É a aproximação honesta do fluxo de ordens: agressão por lado não
  existe em fonte gratuita e estável.
- **Calma** (35%): 100 menos o percentil da volatilidade de queda de 10
  pregões do Ibovespa dentro dos 252 pregões anteriores. Só os retornos
  negativos contam: uma alta forte não é medo (em 05/10/2026 o Ibovespa subiu
  7,4% e a volatilidade comum zerava a Calma por dez pregões).
- **Volume** (25%): ritmo do volume financeiro contra a média de 21 pregões,
  ajustado pela fração do pregão já decorrida, no sentido da maioria.

Este módulo só calcula; o coletor (`app/collectors/mare.py`) baixa os dados e
a página só lê do banco. Calibrar qualquer constante abaixo é uma spec nova,
com evidência, não um ajuste solto.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from app.services.sparkline import build_sparkline

BRT = timezone(timedelta(hours=-3))

# Pesos da spec 027. Somam 1.
PESOS = {"fluxo": 0.40, "calma": 0.35, "volume": 0.25}
NOMES = {"fluxo": "Fluxo", "calma": "Calma", "volume": "Volume"}

# Faixas, da pior para a melhor. O limite inferior pertence à faixa de cima:
# 20 é Medo, 80 é Otimismo extremo.
FAIXAS = ["Pânico", "Medo", "Neutro", "Confiança", "Otimismo extremo"]

# Calma: volatilidade de queda anualizada de 10 retornos diários, comparada com a dos
# 252 pregões anteriores. Com menos de 120 pregões de história, o percentil
# não diz nada e o componente fica ausente.
JANELA_VOLATILIDADE = 10
JANELA_PERCENTIL = 252
MINIMO_PERCENTIL = 120

# Volume: média de 21 pregões; 0,5× ou menos é intensidade zero, 2× ou mais é
# intensidade total. Com menos de 10 pregões na média, fica ausente.
JANELA_MEDIA_VOLUME = 21
MINIMO_MEDIA_VOLUME = 10
RITMO_NEUTRO = 0.5
RITMO_FAIXA = 1.5

# Pregão regular de 10:00 a 17:00 BRT (420 min). A fração mínima evita que o
# primeiro minuto do dia divida o volume por quase zero.
ABERTURA = time(10, 0)
DURACAO_MINUTOS = 420
FRACAO_MINIMA = 0.1

# Amostra: ação com menos de 80% dos pregões da janela fica de fora; com menos
# de 20 ações válidas, Fluxo e Volume ficam ausentes.
COBERTURA_MINIMA = 0.8
MINIMO_ACOES = 20

DIAS_HISTORICO = 21


def faixa(valor: float) -> str:
    """Nome da faixa: 0-19 Pânico, 20-39 Medo, 40-59 Neutro, 60-79 Confiança, 80-100 Otimismo extremo."""
    indice = int(max(0.0, min(100.0, float(valor))) // 20)
    return FAIXAS[min(indice, len(FAIXAS) - 1)]


def _limitar(x: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, x))


def _arredondar(x: float) -> int:
    """Arredonda para o inteiro mais próximo, meio para cima (sem o arredondamento bancário)."""
    return int(math.floor(x + 0.5))


# --------------------------------------------------------------------------
# Componentes
# --------------------------------------------------------------------------


def componente_fluxo(acoes: list[tuple[float, float]]) -> float | None:
    """Fluxo a partir de pares (variação do dia, volume financeiro do dia).

    Ações sem variação (zero) não entram nem no numerador nem no denominador.
    """
    em_alta = sum(fin for var, fin in acoes if var > 0 and fin > 0)
    com_variacao = sum(fin for var, fin in acoes if var != 0 and fin > 0)
    if com_variacao <= 0:
        return None
    return em_alta / com_variacao * 100


def volatilidades(fechamentos: list[float]) -> list[float | None]:
    """Volatilidade de queda anualizada de 10 retornos log, alinhada com os fechamentos.

    Semidesvio com alvo zero: raiz da média dos quadrados dos retornos
    negativos (os positivos entram como zero), vezes raiz de 252. Dez dias
    sem queda dão 0, a menor volatilidade possível. O item i usa os retornos
    que terminam no fechamento i; os primeiros 10 ficam None.
    """
    retornos: list[float | None] = [None]
    for anterior, atual in zip(fechamentos, fechamentos[1:]):
        retornos.append(
            math.log(atual / anterior) if anterior > 0 and atual > 0 else None
        )
    saida: list[float | None] = []
    for i in range(len(fechamentos)):
        trecho = retornos[i - JANELA_VOLATILIDADE + 1 : i + 1] if i >= 1 else []
        janela = [r for r in trecho if r is not None]
        if i < JANELA_VOLATILIDADE or len(janela) < JANELA_VOLATILIDADE:
            saida.append(None)
            continue
        quedas = [min(r, 0.0) ** 2 for r in janela]
        saida.append(math.sqrt(sum(quedas) / len(quedas)) * math.sqrt(252))
    return saida


def componente_calma(sigma_hoje: float | None, janela: list[float]) -> float | None:
    """100 menos o percentil da volatilidade de hoje dentro da janela.

    Igual à menor da janela dá 100; igual à maior dá 0.
    """
    if sigma_hoje is None or len(janela) < MINIMO_PERCENTIL:
        return None
    menores = sum(1 for v in janela if v < sigma_hoje)
    percentil = min(100.0, menores / (len(janela) - 1) * 100)
    return 100 - percentil


def calma_no_indice(sigmas: list[float | None], i: int) -> float | None:
    anteriores = [s for s in sigmas[max(0, i - JANELA_PERCENTIL) : i] if s is not None]
    return componente_calma(sigmas[i], anteriores)


def fracao_do_pregao(agora: datetime, dia: date) -> float:
    """Fração decorrida do pregão de `dia`, vista de `agora`.

    Fora do pregão (antes da abertura do dia seguinte, depois do fechamento,
    fim de semana ou um dia que não é o de hoje) o pregão está completo: 1.
    """
    local = agora.astimezone(BRT)
    if local.date() != dia or local.weekday() >= 5:
        return 1.0
    minutos = (local.hour * 60 + local.minute) - (ABERTURA.hour * 60 + ABERTURA.minute)
    if minutos < 0 or minutos >= DURACAO_MINUTOS:
        return 1.0
    return _limitar(minutos / DURACAO_MINUTOS, FRACAO_MINIMA, 1.0)


def componente_volume(
    volume_hoje: float,
    media_anterior: float | None,
    fracao: float,
    altas: int,
    baixas: int,
) -> float | None:
    """Volume como amplificador da direção da maioria.

    ritmo = volume de hoje / (média × fração do pregão);
    intensidade = (ritmo − 0,5) / 1,5 limitada a [0, 1];
    direção = 2 × altas / (altas + baixas) − 1;
    Volume = 50 + 50 × intensidade × direção.
    """
    if not media_anterior or media_anterior <= 0 or altas + baixas == 0:
        return None
    ritmo = volume_hoje / (media_anterior * max(fracao, FRACAO_MINIMA))
    intensidade = _limitar((ritmo - RITMO_NEUTRO) / RITMO_FAIXA, 0.0, 1.0)
    direcao = 2 * altas / (altas + baixas) - 1
    return 50 + 50 * intensidade * direcao


def indice(
    componentes: dict[str, float | None],
) -> tuple[int | None, dict[str, float], list[str]]:
    """Média ponderada dos componentes presentes, com pesos reescalados.

    Devolve (valor, pesos usados, ausentes). Com menos de dois componentes,
    o valor é None.
    """
    presentes = {k: v for k, v in componentes.items() if v is not None}
    ausentes = [k for k in PESOS if componentes.get(k) is None]
    if len(presentes) < 2:
        return None, {}, ausentes
    soma = sum(PESOS[k] for k in presentes)
    pesos = {k: PESOS[k] / soma for k in presentes}
    valor = sum(pesos[k] * v for k, v in presentes.items())
    return int(_limitar(_arredondar(valor), 0, 100)), pesos, ausentes


# --------------------------------------------------------------------------
# Cálculo completo a partir das séries
# --------------------------------------------------------------------------

# Série de uma ação: dia -> (fechamento, volume em quantidade).
SerieAcao = dict[date, tuple[float, float]]


@dataclass
class Leitura:
    dia: date
    valor: int | None
    componentes: dict[str, float | None]
    pesos: dict[str, float] = field(default_factory=dict)
    ausentes: list[str] = field(default_factory=list)


def _acoes_validas(
    acoes: dict[str, SerieAcao], sessoes: list[date]
) -> dict[str, SerieAcao]:
    minimo = COBERTURA_MINIMA * len(sessoes)
    return {t: s for t, s in acoes.items() if len(s) >= minimo}


class _Calculadora:
    def __init__(self, acoes: dict[str, SerieAcao], ibov: dict[date, float]):
        self.sessoes = sorted({d for s in acoes.values() for d in s})
        self.acoes = _acoes_validas(acoes, self.sessoes)
        self.amostra_ok = len(self.acoes) >= MINIMO_ACOES
        # Volume financeiro total da amostra em cada pregão.
        self.financeiro = {
            d: sum(s[d][0] * s[d][1] for s in self.acoes.values() if d in s)
            for d in self.sessoes
        }
        self.dias_ibov = sorted(ibov)
        self.sigmas = volatilidades([ibov[d] for d in self.dias_ibov])

    def _variacoes(self, dia: date) -> list[tuple[float, float]]:
        pares = []
        for serie in self.acoes.values():
            if dia not in serie:
                continue
            anteriores = [d for d in serie if d < dia]
            if not anteriores:
                continue
            fech_ant = serie[max(anteriores)][0]
            fech, vol = serie[dia]
            if fech_ant > 0:
                pares.append((fech / fech_ant - 1, fech * vol))
        return pares

    def _calma(self, dia: date) -> float | None:
        anteriores = [i for i, d in enumerate(self.dias_ibov) if d <= dia]
        if not anteriores:
            return None
        return calma_no_indice(self.sigmas, anteriores[-1])

    def leitura(self, dia: date, fracao: float) -> Leitura:
        fluxo = volume = None
        if self.amostra_ok and dia in self.financeiro:
            pares = self._variacoes(dia)
            fluxo = componente_fluxo(pares)
            k = self.sessoes.index(dia)
            janela = [
                self.financeiro[d]
                for d in self.sessoes[max(0, k - JANELA_MEDIA_VOLUME) : k]
                if self.financeiro[d] > 0
            ]
            media = (
                sum(janela) / len(janela)
                if len(janela) >= MINIMO_MEDIA_VOLUME
                else None
            )
            altas = sum(1 for var, _ in pares if var > 0)
            baixas = sum(1 for var, _ in pares if var < 0)
            volume = componente_volume(
                self.financeiro[dia], media, fracao, altas, baixas
            )
        componentes = {"fluxo": fluxo, "calma": self._calma(dia), "volume": volume}
        valor, pesos, ausentes = indice(componentes)
        return Leitura(dia, valor, componentes, pesos, ausentes)


def calcular(
    acoes: dict[str, SerieAcao], ibov: dict[date, float], agora: datetime
) -> tuple[Leitura | None, list[Leitura]]:
    """Leitura do último pregão e as leituras dos 21 pregões anteriores.

    O último pregão é o mais recente da amostra de ações (ou do Ibovespa, se a
    amostra faltar). O histórico usa o pregão inteiro (fração 1).
    """
    calc = _Calculadora(acoes, ibov)
    dias = calc.sessoes or calc.dias_ibov
    if not dias:
        return None, []
    hoje = dias[-1]
    atual = calc.leitura(hoje, fracao_do_pregao(agora, hoje))
    historico = [
        leitura
        for d in dias[-DIAS_HISTORICO - 1 : -1]
        if (leitura := calc.leitura(d, 1.0)).valor is not None
    ]
    return (atual if atual.valor is not None else None), historico


# --------------------------------------------------------------------------
# Dados para a página e para o /api/snapshot
# --------------------------------------------------------------------------


def _numero(x: float | None, casas: int = 1) -> float | None:
    return None if x is None else round(x, casas)


def snapshot(dado: Any) -> dict[str, Any]:
    """Chave `mare` do /api/snapshot (invariantes da spec 027)."""
    componentes = {
        "fluxo": _numero(dado.fluxo),
        "calma": _numero(dado.calma),
        "volume": _numero(dado.volume),
    }
    _, pesos, ausentes = indice(
        {"fluxo": dado.fluxo, "calma": dado.calma, "volume": dado.volume}
    )
    return {
        "coletado_em": dado.timestamp.isoformat(),
        "fonte": dado.fonte,
        "valor": dado.valor,
        "faixa": faixa(dado.valor),
        "componentes": componentes,
        "pesos": {k: round(v, 4) for k, v in pesos.items()},
        "parcial": bool(ausentes),
        "ausentes": ausentes,
        "historico": json.loads(dado.historico_json or "[]"),
    }


def view(dado: Any) -> dict[str, Any] | None:
    if dado is None:
        return None
    snap = snapshot(dado)
    historico = [p["valor"] for p in snap["historico"]]
    serie = historico + [dado.valor]
    comparacao = None
    if len(historico) >= 5:
        antes = historico[-5]
        comparacao = f"há 5 pregões: {antes} · {faixa(antes)}"
    return {
        "valor": dado.valor,
        "faixa": snap["faixa"],
        "faixas": FAIXAS,
        "componentes": [
            {
                "nome": NOMES[k],
                "valor": None
                if snap["componentes"][k] is None
                else _arredondar(snap["componentes"][k]),
                "peso": round(PESOS[k] * 100),
            }
            for k in ("fluxo", "calma", "volume")
        ],
        "parcial": snap["parcial"],
        "ausentes": ", ".join(NOMES[k] for k in snap["ausentes"]),
        "sparkline": build_sparkline(serie),
        "resumo_serie": (
            f"Maré nos últimos {len(serie)} pregões, de {min(serie)} a {max(serie)}"
            if len(serie) >= 2
            else ""
        ),
        "comparacao": comparacao,
        "fonte": dado.fonte,
        "time": dado.timestamp.astimezone(BRT).strftime("%d/%m/%Y %H:%M BRT"),
    }


def get_mare_view() -> dict[str, Any] | None:
    from app.database import get_latest_mare_data

    return view(get_latest_mare_data())
