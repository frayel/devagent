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
        if anterior > 0 and atual > 0:
            r = math.log(atual / anterior)
            retornos.append(r if abs(r) < 0.12 else None)
        else:
            retornos.append(None)
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
    heatmap: list[dict] = field(default_factory=list)


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
        heatmap: list[dict[str, float | str]] = []
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

            ativos: list[dict[str, float | str]] = []
            for ticker, serie in self.acoes.items():
                if dia not in serie:
                    continue
                anteriores = [d for d in serie if d < dia]
                if not anteriores:
                    continue
                fech_ant = serie[max(anteriores)][0]
                fech, vol = serie[dia]
                if fech_ant > 0:
                    ativos.append(
                        {
                            "ticker": ticker,
                            "variacao": float((fech / fech_ant - 1) * 100),
                            "financeiro": float(fech * vol),
                        }
                    )
            ativos.sort(key=lambda x: float(x["financeiro"]), reverse=True)  # type: ignore
            total_fin = sum(float(a["financeiro"]) for a in ativos[:10])  # type: ignore
            for i, a in enumerate(ativos[:10]):
                a["peso"] = float(a["financeiro"]) / total_fin if total_fin > 0 else 0.0  # type: ignore
                heatmap.append(a)

        componentes = {"fluxo": fluxo, "calma": self._calma(dia), "volume": volume}
        valor, pesos, ausentes = indice(componentes)
        return Leitura(dia, valor, componentes, pesos, ausentes, heatmap)


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
# Níveis: Ondas e Maré (spec 174a)
# --------------------------------------------------------------------------

# Janela de cada nível, em pregões completos, e o mínimo de leituras para o
# nível existir. Abaixo do mínimo o nível está em formação (None).
JANELAS_NIVEL = {"ondas": 21, "mare": 252}
MINIMO_LEITURAS = {"ondas": 15, "mare": 189}
# Componente presente em menos desta fração dos dias da janela fica ausente.
PRESENCA_MINIMA = 0.75
TOP_HEATMAP = 10


def heatmap_janela(
    acoes: dict[str, SerieAcao], janela: list[date], anterior: date
) -> list[dict[str, float | str]]:
    """As 10 ações de maior volume financeiro somado na janela.

    `variacao` vai do fechamento do pregão `anterior` (o anterior ao primeiro
    da janela) ao do último pregão da janela, em %; `financeiro` é a soma de
    fechamento × volume nos pregões da janela, em reais; `peso` é a fração do
    financeiro das 10. Ação sem um dos dois fechamentos fica de fora.
    """
    if not janela:
        return []
    ultimo = janela[-1]
    ativos: list[dict[str, float | str]] = []
    for ticker, serie in acoes.items():
        if anterior not in serie or ultimo not in serie:
            continue
        fech_ant = serie[anterior][0]
        if fech_ant <= 0:
            continue
        financeiro = sum(serie[d][0] * serie[d][1] for d in janela if d in serie)
        ativos.append(
            {
                "ticker": ticker,
                "variacao": float((serie[ultimo][0] / fech_ant - 1) * 100),
                "financeiro": float(financeiro),
            }
        )
    ativos.sort(key=lambda a: float(a["financeiro"]), reverse=True)
    topo = ativos[:TOP_HEATMAP]
    total = sum(float(a["financeiro"]) for a in topo)
    for a in topo:
        a["peso"] = float(a["financeiro"]) / total if total > 0 else 0.0
    return topo


def janela_nivel(leituras: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
    """As `n` leituras mais recentes com valor: as que dão o nível e os pontos
    do gráfico de Ondas e Maré (spec 175), para os dois nunca divergirem."""
    return [x for x in leituras if x.get("valor") is not None][-n:]


def nivel(
    leituras: list[dict[str, Any]],
    n: int,
    minimo: int,
    heatmap: list[dict] | None = None,
) -> dict[str, Any] | None:
    """Nível a partir das leituras diárias (em ordem crescente de data).

    O valor é a média dos `valor` das `n` leituras mais recentes, arredondada
    meio para cima; cada componente é a média dos dias em que existe, e fica
    ausente se existe em menos de 75% dos dias. Com menos de `minimo`
    leituras, o nível está em formação e a função devolve None.
    """
    janela = janela_nivel(leituras, n)
    if len(janela) < minimo:
        return None
    valor = int(
        _limitar(_arredondar(sum(x["valor"] for x in janela) / len(janela)), 0, 100)
    )
    medias: dict[str, float | None] = {}
    for k in PESOS:
        presentes = [x[k] for x in janela if x.get(k) is not None]
        if presentes and len(presentes) / len(janela) >= PRESENCA_MINIMA:
            medias[k] = sum(presentes) / len(presentes)
        else:
            medias[k] = None
    _, pesos, ausentes = indice(medias)
    return {
        "valor": valor,
        "faixa": faixa(valor),
        "pregoes": len(janela),
        "de": janela[0]["data"],
        "ate": janela[-1]["data"],
        "componentes": {k: _numero(v) for k, v in medias.items()},
        "pesos": {k: round(v, 4) for k, v in pesos.items()},
        "ausentes": ausentes,
        "heatmap": heatmap or [],
    }


def niveis(historico: dict[str, Any] | None) -> dict[str, dict[str, Any] | None]:
    """`niveis` do /api/snapshot a partir do snapshot `mare_historico`."""
    if not historico:
        return {k: None for k in JANELAS_NIVEL}
    leituras = historico.get("leituras") or []
    return {
        k: nivel(
            leituras,
            n,
            MINIMO_LEITURAS[k],
            historico.get(f"heatmap_{k}") or [],
        )
        for k, n in JANELAS_NIVEL.items()
    }


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
        "heatmap": json.loads(getattr(dado, "ativos_json", "[]") or "[]"),
        "historico": json.loads(dado.historico_json or "[]"),
    }


def _peso_visivel(
    k: str, valor: float | None, pesos_usados: dict[str, float]
) -> int | None:
    """Percentual inteiro do peso que o componente teve no valor (spec 144).

    Ausente não tem peso. Sem pesos usados (leitura com menos de dois
    componentes, que o coletor não grava), vale o nominal da 027.
    """
    if valor is None:
        return None
    return _arredondar(pesos_usados.get(k, PESOS[k]) * 100)


def view(dado: Any) -> dict[str, Any] | None:
    if dado is None:
        return None
    snap = snapshot(dado)
    # Peso visível (spec 144): o que entrou na conta, não o nominal da 027.
    _, pesos_usados, _ = indice(
        {"fluxo": dado.fluxo, "calma": dado.calma, "volume": dado.volume}
    )
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
                "peso": _peso_visivel(k, snap["componentes"][k], pesos_usados),
            }
            for k in ("fluxo", "calma", "volume")
        ],
        "parcial": snap["parcial"],
        "cobertura": f"{len(PESOS) - len(snap['ausentes'])} de {len(PESOS)} componentes",
        "heatmap": snap.get("heatmap", []),
        "ausentes": ", ".join(NOMES[k] for k in snap["ausentes"]),
        "fonte": dado.fonte,
        "time": dado.timestamp.astimezone(BRT).strftime("%d/%m/%Y %H:%M:%S BRT"),
    }


def get_mare_view() -> dict[str, Any] | None:
    from app.database import get_latest_mare_data

    return view(get_latest_mare_data())


# --------------------------------------------------------------------------
# Seletor Marolas, Ondas e Maré no card (spec 174b)
# --------------------------------------------------------------------------

# (nível, rótulo, janela em letra menor). Marolas é a leitura de hoje (027).
NIVEIS_SELETOR = [
    ("marolas", "Marolas", "hoje"),
    ("ondas", "Ondas", "21 pregões"),
    ("mare", "Maré", "252 pregões"),
]
NIVEL_PADRAO = "marolas"
LEGENDA_HEATMAP = {
    "marolas": "volume financeiro do dia",
    "ondas": "volume financeiro dos últimos 21 pregões",
    "mare": "volume financeiro dos últimos 252 pregões",
}


def nivel_valido(escolhido: str | None) -> str:
    """Valor de `nivel` da query; desconhecido ou ausente vale Marolas."""
    validos = {n for n, _, _ in NIVEIS_SELETOR}
    return escolhido if escolhido in validos else NIVEL_PADRAO


def legenda_heatmap(nivel_escolhido: str) -> str:
    return (
        f"Área: {LEGENDA_HEATMAP[nivel_valido(nivel_escolhido)]}, entre os 10 "
        "maiores da cesta de 30 ações · cor: variação do preço"
    )


def _dd_mm(iso: str) -> str:
    d = date.fromisoformat(str(iso)[:10])
    return f"{d.day:02d}/{d.month:02d}"


# --------------------------------------------------------------------------
# O gráfico no tempo do nível (spec 175)
# --------------------------------------------------------------------------

# Pontos intradiários: um por coleta do pregão, das 10:00 ao leilão de
# fechamento (18:15, o FIM_PREGAO do agendador), no máximo 40 por dia.
INICIO_INTRADIA = "10:00"
FIM_INTRADIA = "18:15"
MAXIMO_PONTOS_INTRADIA = 40
# Marolas antes da segunda coleta: procura o pregão mais recente com curva.
PREGOES_PROCURADOS = 5
MINIMO_LEITURAS_MES = 5
MESES = [
    "jan",
    "fev",
    "mar",
    "abr",
    "mai",
    "jun",
    "jul",
    "ago",
    "set",
    "out",
    "nov",
    "dez",
]
SEM_CURVA = "A curva do dia começa na segunda coleta do pregão"


def acrescentar_ponto(
    pontos: list[dict[str, Any]], hora: str, valor: int
) -> list[dict[str, Any]]:
    """Os pontos do dia com `{hora, valor}`, em ordem crescente de hora.

    A mesma `hora` substitui o ponto anterior; um ponto novo além do 40º não
    entra.
    """
    outros = [p for p in pontos if p.get("hora") != hora]
    if len(outros) == len(pontos) and len(pontos) >= MAXIMO_PONTOS_INTRADIA:
        return sorted(pontos, key=lambda p: p["hora"])
    return sorted(outros + [{"hora": hora, "valor": valor}], key=lambda p: p["hora"])


def hora_intradia(timestamp: datetime) -> tuple[date, str] | None:
    """(dia BRT, "HH:MM") de uma coleta dentro do pregão; fora dele, None."""
    from app import calendario

    local = timestamp.astimezone(BRT)
    hora = local.strftime("%H:%M")
    if not calendario.e_pregao(local.date()):
        return None
    if not INICIO_INTRADIA <= hora <= FIM_INTRADIA:
        return None
    return local.date(), hora


def hoje_brt() -> date:
    return datetime.now(timezone.utc).astimezone(BRT).date()


def _com_curva(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and len(payload.get("pontos") or []) >= 2  # type: ignore[union-attr]


def buscar_intradia(hoje: date, data_passada: bool = False) -> dict[str, Any] | None:
    """O `mare_intradia` que o Marolas desenha: `{data, pontos}` ou None.

    Numa data passada, só o daquela data. Hoje, o de hoje ou o do pregão mais
    recente com dois pontos entre os 5 anteriores, lidos por data numa consulta
    (`listar_datas` ignoraria os snapshots `ao_vivo`).
    """
    from app import banco, calendario

    dias = [hoje]
    if not data_passada:
        d = hoje
        for _ in range(PREGOES_PROCURADOS):
            d = calendario.pregao_anterior(d)
            dias.append(d)
    # Uma consulta para todas as datas (spec 153).
    lidos = banco.ler_snapshots_datas("mare_intradia", dias)
    for d in dias:
        payload = lidos.get(d)
        if _com_curva(payload):
            return {"data": d.isoformat(), "pontos": list(payload["pontos"])}  # type: ignore[index]
    return None


def _mes(chave: tuple[int, int]) -> str:
    return f"{MESES[chave[1] - 1]}/{chave[0] % 100:02d}"


def serie_mensal(janela: list[dict[str, Any]]) -> list[tuple[str, int]]:
    """(rótulo `nov/25`, média do mês) de cada mês civil da janela, em ordem.

    Mês com menos de 5 leituras sai (só acontece nas bordas).
    """
    meses: dict[tuple[int, int], list[int]] = {}
    for x in janela:
        d = date.fromisoformat(str(x["data"])[:10])
        meses.setdefault((d.year, d.month), []).append(x["valor"])
    return [
        (_mes(k), _arredondar(sum(v) / len(v)))
        for k, v in sorted(meses.items())
        if len(v) >= MINIMO_LEITURAS_MES
    ]


def _variacao(delta: int) -> tuple[str, int]:
    if delta == 0:
        return "estável", 0
    sinal = "+" if delta > 0 else "\u2212"
    return f"{sinal}{abs(delta)} pontos", (1 if delta > 0 else -1)


def grafico(
    pontos: list[tuple[str, int]], titulo: str, referencia: float | None = None
) -> dict[str, Any] | None:
    """O gráfico de um nível a partir de (rótulo, valor) em ordem do tempo.

    `titulo` abre a frase (`Hoje`, `21 pregões`, `13 meses`); `referencia` é
    o valor do gauge, desenhado como linha tracejada em Ondas e Maré.
    """
    valores = [v for _, v in pontos]
    desenho = build_sparkline([float(v) for v in valores], referencia)
    if desenho is None:
        return None
    (inicio, primeiro), (fim, ultimo) = pontos[0], pontos[-1]
    variacao, sinal = _variacao(ultimo - primeiro)
    prefixo = f"{titulo}: de {primeiro} ({inicio}) para {ultimo} ({fim}), "
    return {
        "pontos": desenho["pontos"],
        "referencia_y": desenho.get("referencia_y"),
        "inicio": inicio,
        "fim": fim,
        "prefixo": prefixo,
        "variacao": variacao,
        "sinal": sinal,
        "resumo": prefixo + variacao,
        "faixa": f"mín {min(valores)} · máx {max(valores)}",
    }


def grafico_marolas(
    intradia: dict[str, Any] | None, hoje: date | None
) -> dict[str, Any] | None:
    if not _com_curva(intradia):
        return None
    assert intradia is not None
    dia = date.fromisoformat(intradia["data"])
    titulo = "Hoje" if dia == hoje else f"Pregão de {dia.day:02d}/{dia.month:02d}"
    pontos = [(p["hora"], int(p["valor"])) for p in intradia["pontos"]]
    return grafico(pontos, titulo)


def grafico_nivel(
    historico: dict[str, Any] | None, escolhido: str, valor: int
) -> dict[str, Any] | None:
    janela = janela_nivel(
        (historico or {}).get("leituras") or [], JANELAS_NIVEL[escolhido]
    )
    if escolhido == "ondas":
        pontos = [(_dd_mm(x["data"]), int(x["valor"])) for x in janela]
        titulo = f"{len(pontos)} pregões"
    else:
        pontos = serie_mensal(janela)
        titulo = f"{len(pontos)} meses"
    if len(pontos) < 2:
        return None
    return grafico(pontos, titulo, valor)


def view_nivel(
    base: dict[str, Any] | None,
    historico: dict[str, Any] | None,
    nivel_escolhido: str | None,
    data_passada: bool = False,
    intradia: dict[str, Any] | None = None,
    hoje: date | None = None,
) -> dict[str, Any] | None:
    """O card da Maré no nível escolhido.

    `base` é o `view` de hoje (Marolas). Ondas e Maré trocam valor, faixa,
    componentes e heatmap pelos de `niveis` (os mesmos do /api/snapshot).
    Cada nível traz o seu gráfico (spec 175): Marolas, a curva de
    `intradia`; Ondas e Maré, as leituras da janela do gauge. Nível em
    formação vira `estado="formacao"`; numa data passada sem
    `mare_historico`, `estado="sem_registro"`.
    """
    escolhido = nivel_valido(nivel_escolhido)
    if escolhido == NIVEL_PADRAO:
        if base is None:
            return None
        curva = grafico_marolas(intradia, None if data_passada else hoje)
        return {
            **base,
            "nivel": escolhido,
            "legenda": legenda_heatmap(escolhido),
            "grafico": curva,
            "sem_grafico": SEM_CURVA if curva is None and not data_passada else None,
        }

    comum: dict[str, Any] = {
        "fonte": "",
        "time": "",
        "faixas": FAIXAS,
        **(base or {}),
        "nivel": escolhido,
        "legenda": legenda_heatmap(escolhido),
        "contexto": None,
        "estado": None,
        "grafico": None,
        "sem_grafico": None,
    }
    if historico is None and data_passada:
        return {**comum, "estado": "sem_registro"}
    n = niveis(historico)[escolhido]
    if n is None:
        gravadas = len((historico or {}).get("leituras") or [])
        return {
            **comum,
            "estado": "formacao",
            "formacao": (
                f"Histórico da maré em formação: {gravadas} de "
                f"{MINIMO_LEITURAS[escolhido]} pregões"
            ),
        }
    medias = n["componentes"]
    return {
        **comum,
        "valor": n["valor"],
        "faixa": n["faixa"],
        "componentes": [
            {
                "nome": NOMES[k],
                "valor": None if medias.get(k) is None else _arredondar(medias[k]),
                "peso": _peso_visivel(k, medias.get(k), n["pesos"]),
            }
            for k in ("fluxo", "calma", "volume")
        ],
        "parcial": bool(n["ausentes"]),
        "ausentes": ", ".join(NOMES[k] for k in n["ausentes"]),
        "cobertura": f"{len(PESOS) - len(n['ausentes'])} de {len(PESOS)} componentes",
        "heatmap": n["heatmap"],
        "grafico": grafico_nivel(historico, escolhido, n["valor"]),
        "contexto": (
            f"média de {n['pregoes']} pregões completos, "
            f"de {_dd_mm(n['de'])} a {_dd_mm(n['ate'])}"
        ),
    }


def seletor(
    params: dict[str, str], nivel_escolhido: str | None
) -> list[dict[str, Any]]:
    """As três opções do seletor, cada uma um link para a própria página.

    O link é só a query (`?…`), então vale em `/` e em `/mare`; os outros
    parâmetros (`data`, `aba`) seguem junto.
    """
    from urllib.parse import urlencode

    escolhido = nivel_valido(nivel_escolhido)
    outros = {k: v for k, v in params.items() if k != "nivel"}
    return [
        {
            "nivel": n,
            "rotulo": rotulo,
            "janela": janela,
            "href": "?" + urlencode({**outros, "nivel": n}),
            "ativo": n == escolhido,
        }
        for n, rotulo, janela in NIVEIS_SELETOR
    ]
