"""Maré do mercado (spec 027): cálculo, coletor, snapshot e painel, sem internet."""

from __future__ import annotations

import json
import math
import re
from datetime import date, datetime, timedelta, timezone

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.collectors import mare as coletor
from app.collectors.highlights import TICKERS
from app.database import MareData, get_latest_mare_data, save_mare_data
from app.services import mare

BRT = mare.BRT


# --------------------------------------------------------------------------
# Faixas
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("valor", "nome"),
    [
        (0, "Pânico"),
        (19, "Pânico"),
        (20, "Medo"),
        (39, "Medo"),
        (40, "Neutro"),
        (59, "Neutro"),
        (60, "Confiança"),
        (79, "Confiança"),
        (80, "Otimismo extremo"),
        (100, "Otimismo extremo"),
    ],
)
def test_faixas(valor, nome):
    assert mare.faixa(valor) == nome


# --------------------------------------------------------------------------
# Componentes
# --------------------------------------------------------------------------


def test_fluxo_tudo_em_alta_tudo_em_queda_e_meio_a_meio():
    assert mare.componente_fluxo([(0.01, 100.0), (0.02, 300.0)]) == 100
    assert mare.componente_fluxo([(-0.01, 100.0), (-0.02, 300.0)]) == 0
    assert mare.componente_fluxo([(0.01, 200.0), (-0.02, 200.0)]) == 50


def test_fluxo_ignora_acoes_paradas_e_sem_variacao_e_none():
    assert mare.componente_fluxo([(0.0, 500.0), (0.01, 100.0)]) == 100
    assert mare.componente_fluxo([(0.0, 500.0)]) is None


def test_calma_extremos_da_janela():
    janela = [0.10 + i * 0.001 for i in range(252)]
    assert mare.componente_calma(min(janela), janela) == 100
    assert mare.componente_calma(max(janela), janela) == 0
    assert mare.componente_calma(0.01, janela) == 100
    assert mare.componente_calma(0.99, janela) == 0


def test_calma_sem_historia_suficiente_e_none():
    assert mare.componente_calma(0.2, [0.1] * 50) is None
    assert mare.componente_calma(None, [0.1] * 252) is None


def test_volatilidade_de_queda_de_dez_retornos():
    fech = [100.0 * (1.01 if i % 2 else 0.99) ** 1 for i in range(12)]
    sig = mare.volatilidades(fech)
    assert sig[:10] == [None] * 10
    retornos = [math.log(b / a) for a, b in zip(fech, fech[1:])]
    janela = retornos[1:11]
    esperado = math.sqrt(sum(min(r, 0) ** 2 for r in janela) / 10) * math.sqrt(252)
    assert sig[11] == pytest.approx(esperado)


def test_dez_dias_sem_queda_tem_volatilidade_zero():
    fech = [100.0 * 1.01**i for i in range(12)]
    assert mare.volatilidades(fech)[11] == 0


def test_alta_forte_nao_derruba_a_calma():
    """Caso real de 05/10/2026: Ibovespa +7,4% num dia, quedas pequenas na janela."""
    dias = _dias_uteis(date(2026, 10, 6), 300)
    fech, v = {}, 100_000.0
    for i, d in enumerate(dias[:-10]):
        v *= 1 + (0.012 if i % 2 else -0.012)
        fech[d] = v
    for d, r in zip(
        dias[-10:], [-0.86, -1.0, -0.27, -0.27, 0.46, 1.36, 0.46, 2.59, 7.42, -0.47]
    ):
        v *= math.exp(r / 100)
        fech[d] = v
    sig = mare.volatilidades([fech[d] for d in dias])
    calma = mare.calma_no_indice(sig, len(dias) - 1)
    assert calma is not None and calma > 60


def test_queda_forte_zera_a_calma():
    dias = _dias_uteis(date(2026, 10, 6), 300)
    fech, v = {}, 100_000.0
    for i, d in enumerate(dias):
        v *= 1 + (0.006 if i % 2 else -0.006)
        if i == len(dias) - 2:
            v *= 0.93
        fech[d] = v
    sig = mare.volatilidades([fech[d] for d in dias])
    assert mare.calma_no_indice(sig, len(dias) - 1) == 0


@pytest.mark.parametrize(
    ("ritmo", "altas", "baixas", "esperado"),
    [
        (2.0, 10, 0, 100),
        (2.0, 0, 10, 0),
        (0.5, 10, 0, 50),
        (0.5, 0, 10, 50),
        (1.25, 10, 0, 75),
        (3.0, 5, 5, 50),
    ],
)
def test_volume_amplifica_a_direcao(ritmo, altas, baixas, esperado):
    assert mare.componente_volume(ritmo * 1000, 1000, 1.0, altas, baixas) == (
        pytest.approx(esperado)
    )


def test_volume_ajusta_pela_hora_do_pregao():
    # 11:00 BRT: 60 de 420 minutos, fração 1/7.
    agora = datetime(2026, 10, 6, 11, 0, tzinfo=BRT)
    fracao = mare.fracao_do_pregao(agora, date(2026, 10, 6))
    assert fracao == pytest.approx(1 / 7)
    # volume igual a 1/7 da média: ritmo 1,0 -> intensidade 1/3
    v = mare.componente_volume(1000 / 7, 1000, fracao, 10, 0)
    assert v == pytest.approx(50 + 50 * (1.0 - 0.5) / 1.5)


@pytest.mark.parametrize(
    ("quando", "esperado"),
    [
        (datetime(2026, 10, 6, 9, 30, tzinfo=BRT), 1.0),  # antes da abertura
        (datetime(2026, 10, 6, 10, 5, tzinfo=BRT), 0.1),  # fração mínima
        (datetime(2026, 10, 6, 13, 30, tzinfo=BRT), 0.5),
        (datetime(2026, 10, 6, 17, 30, tzinfo=BRT), 1.0),  # depois do fechamento
        (datetime(2026, 10, 10, 13, 0, tzinfo=BRT), 1.0),  # sábado
    ],
)
def test_fracao_do_pregao(quando, esperado):
    assert mare.fracao_do_pregao(quando, quando.date()) == pytest.approx(esperado)


def test_fracao_e_um_para_pregao_de_outro_dia():
    agora = datetime(2026, 10, 6, 13, 0, tzinfo=BRT)
    assert mare.fracao_do_pregao(agora, date(2026, 10, 5)) == 1.0


# --------------------------------------------------------------------------
# Índice
# --------------------------------------------------------------------------


def test_indice_completo():
    valor, pesos, ausentes = mare.indice({"fluxo": 70, "calma": 60, "volume": 80})
    assert valor == round(0.4 * 70 + 0.35 * 60 + 0.25 * 80)
    assert sum(pesos.values()) == pytest.approx(1)
    assert ausentes == []


def test_indice_sem_ibovespa_reescala_os_pesos():
    valor, pesos, ausentes = mare.indice({"fluxo": 80, "calma": None, "volume": 40})
    assert ausentes == ["calma"]
    assert pesos["fluxo"] == pytest.approx(40 / 65)
    assert pesos["volume"] == pytest.approx(25 / 65)
    assert valor == round(80 * 40 / 65 + 40 * 25 / 65)


def test_indice_com_um_componente_so_e_none():
    assert mare.indice({"fluxo": 80, "calma": None, "volume": None})[0] is None


# --------------------------------------------------------------------------
# Cálculo sobre séries
# --------------------------------------------------------------------------


def _dias_uteis(fim: date, n: int) -> list[date]:
    dias, d = [], fim
    while len(dias) < n:
        if d.weekday() < 5:
            dias.append(d)
        d -= timedelta(days=1)
    return dias[::-1]


def _cesta(dias: list[date], ultimo_sobe: bool, volume_ultimo: float = 1.0):
    """30 ações com preço oscilando e volume constante; o último dia sobe ou cai."""
    cesta = {}
    for k, t in enumerate(TICKERS[:30]):
        serie = {}
        preco = 20.0 + k
        for i, d in enumerate(dias):
            preco *= 1.004 if (i + k) % 2 else 0.996
            vol = 1000.0 * (volume_ultimo if i == len(dias) - 1 else 1.0)
            serie[d] = (preco, vol)
        ultimo = dias[-1]
        anterior = serie[dias[-2]][0]
        serie[ultimo] = (anterior * (1.02 if ultimo_sobe else 0.98), serie[ultimo][1])
        cesta[t] = serie
    return cesta


def _ibov(dias: list[date], choque_final: float = 0.0):
    fech, v = {}, 100_000.0
    for i, d in enumerate(dias):
        v *= 1 + (0.006 if i % 2 else -0.006)
        if i >= len(dias) - 10:
            v *= 1 + choque_final * (1 if i % 2 else -1)
        fech[d] = v
    return fech


AGORA = datetime(2026, 10, 6, 20, 0, tzinfo=timezone.utc)  # 17:00 BRT, pregão completo


def test_dia_de_alta_calma_e_volume_forte_e_otimismo():
    dias = _dias_uteis(date(2026, 10, 6), 300)
    atual, historico = mare.calcular(
        _cesta(dias[-63:], ultimo_sobe=True, volume_ultimo=2.5), _ibov(dias), AGORA
    )
    assert atual is not None
    assert atual.dia == date(2026, 10, 6)
    assert atual.componentes["fluxo"] == 100
    assert atual.componentes["volume"] == pytest.approx(100)
    assert atual.ausentes == []
    assert mare.faixa(atual.valor) in ("Confiança", "Otimismo extremo")
    assert len(historico) == mare.DIAS_HISTORICO
    assert historico[-1].dia == date(2026, 10, 5)


def test_dia_de_queda_volatil_e_pesado_e_panico():
    dias = _dias_uteis(date(2026, 10, 6), 300)
    atual, _ = mare.calcular(
        _cesta(dias[-63:], ultimo_sobe=False, volume_ultimo=2.5),
        _ibov(dias, choque_final=0.03),
        AGORA,
    )
    assert atual is not None
    assert atual.componentes["fluxo"] == 0
    assert atual.componentes["calma"] == 0
    assert atual.componentes["volume"] == pytest.approx(0)
    assert atual.valor == 0
    assert mare.faixa(atual.valor) == "Pânico"


def test_sem_ibovespa_sai_parcial():
    dias = _dias_uteis(date(2026, 10, 6), 63)
    atual, _ = mare.calcular(_cesta(dias, ultimo_sobe=True), {}, AGORA)
    assert atual is not None
    assert atual.ausentes == ["calma"]
    assert atual.pesos["fluxo"] == pytest.approx(40 / 65)


def test_amostra_pequena_tira_fluxo_e_volume_e_sem_indice():
    dias = _dias_uteis(date(2026, 10, 6), 300)
    pequena = dict(list(_cesta(dias[-63:], ultimo_sobe=True).items())[:10])
    atual, historico = mare.calcular(pequena, _ibov(dias), AGORA)
    assert atual is None
    assert historico == []


def test_acao_com_pouca_historia_fica_fora():
    dias = _dias_uteis(date(2026, 10, 6), 63)
    cesta = _cesta(dias, ultimo_sobe=True)
    # uma ação que só existe nos últimos 10 pregões e despenca
    cesta["NOVA3"] = {d: (10.0 if d != dias[-1] else 5.0, 1e9) for d in dias[-10:]}
    atual, _ = mare.calcular(cesta, {}, AGORA)
    assert atual.componentes["fluxo"] == 100


# --------------------------------------------------------------------------
# Coletor (HTTP mockado)
# --------------------------------------------------------------------------


def _epoch(d: date) -> int:
    return int(datetime(d.year, d.month, d.day, 13, 0, tzinfo=timezone.utc).timestamp())


def _spark(cesta, lote):
    return {
        "spark": {
            "result": [
                {
                    "symbol": f"{t}.SA",
                    "response": [
                        {
                            "timestamp": [_epoch(d) for d in sorted(cesta[t])],
                            "indicators": {
                                "quote": [
                                    {
                                        "close": [
                                            cesta[t][d][0] for d in sorted(cesta[t])
                                        ],
                                        "volume": [
                                            cesta[t][d][1] for d in sorted(cesta[t])
                                        ],
                                    }
                                ]
                            },
                        }
                    ],
                }
                for t in lote
                if t in cesta
            ]
        }
    }


def _chart(ibov):
    dias = sorted(ibov)
    return {
        "chart": {
            "result": [
                {
                    "timestamp": [_epoch(d) for d in dias],
                    "indicators": {"quote": [{"close": [ibov[d] for d in dias]}]},
                }
            ]
        }
    }


@pytest.fixture
def sem_espera(monkeypatch):
    monkeypatch.setattr("app.collectors.utils.MIN_DELAY", 0.0)
    monkeypatch.setattr("app.collectors.utils._last_request_time", {})
    monkeypatch.delenv("BRAPI_TOKEN", raising=False)


def _mock_cesta(cesta):
    def responder(request):
        simbolos = request.url.params["symbols"].split(",")
        lote = [s.replace(".SA", "") for s in simbolos]
        return httpx.Response(200, json=_spark(cesta, lote))

    respx.get(
        url__regex=r"https://query1\.finance\.yahoo\.com/v7/finance/spark.*"
    ).mock(side_effect=responder)


@respx.mock
def test_coletor_grava_a_mare(sem_espera):
    dias = _dias_uteis(date(2026, 10, 6), 300)
    _mock_cesta(_cesta(dias[-63:], ultimo_sobe=True, volume_ultimo=2.5))
    respx.get(
        url__regex=r"https://query2\.finance\.yahoo\.com/v8/finance/chart/.*"
    ).mock(return_value=httpx.Response(200, json=_chart(_ibov(dias))))
    dado = coletor.coletar(AGORA)
    assert dado is not None
    assert dado.fonte == "yfinance"
    assert 0 <= dado.valor <= 100
    historico = json.loads(dado.historico_json)
    assert len(historico) == 21
    assert historico[-1]["data"] == "2026-10-05"


@respx.mock
def test_coletor_sem_ibovespa_grava_parcial(sem_espera):
    dias = _dias_uteis(date(2026, 10, 6), 63)
    _mock_cesta(_cesta(dias, ultimo_sobe=True))
    respx.get(url__regex=r"https://query2\.finance\.yahoo\.com/.*").mock(
        return_value=httpx.Response(500)
    )
    dado = coletor.coletar(AGORA)
    assert dado is not None
    assert dado.calma is None
    assert dado.fluxo == 100


@respx.mock
def test_coletor_com_fontes_fora_nao_grava(sem_espera, monkeypatch):
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)
    respx.get(url__regex=r"https://query[12]\.finance\.yahoo\.com/.*").mock(
        side_effect=httpx.ConnectTimeout("fora")
    )
    assert coletor.collect_and_save() is False
    assert get_latest_mare_data() is None


@respx.mock
def test_coletor_ignora_resposta_malformada(sem_espera):
    respx.get(url__regex=r"https://query1\.finance\.yahoo\.com/.*").mock(
        return_value=httpx.Response(200, json={"spark": {"result": [{"symbol": "X"}]}})
    )
    respx.get(url__regex=r"https://query2\.finance\.yahoo\.com/.*").mock(
        return_value=httpx.Response(200, json={"chart": {"result": []}})
    )
    assert coletor.coletar(AGORA) is None


# --------------------------------------------------------------------------
# Snapshot e página
# --------------------------------------------------------------------------


def _gravar(valor=68, fluxo=74.2, calma=61.0, volume=67.4, n_hist=21):
    dias = _dias_uteis(date(2026, 10, 5), n_hist)
    historico = [{"data": d.isoformat(), "valor": 40 + i} for i, d in enumerate(dias)]
    save_mare_data(
        MareData(
            timestamp=datetime(2026, 10, 6, 17, 30, tzinfo=timezone.utc),
            valor=valor,
            fluxo=fluxo,
            calma=calma,
            volume=volume,
            historico_json=json.dumps(historico),
            fonte="yfinance",
        )
    )


def _cliente():
    from app.main import app

    return TestClient(app)


def test_snapshot_cumpre_as_invariantes():
    _gravar()
    m = _cliente().get("/api/snapshot").json()["paineis"]["mare"]
    for chave in (
        "coletado_em",
        "fonte",
        "valor",
        "faixa",
        "componentes",
        "pesos",
        "parcial",
        "ausentes",
        "historico",
    ):
        assert chave in m
    assert m["valor"] == 68 and m["faixa"] == "Confiança"
    assert sum(m["pesos"].values()) == pytest.approx(1, abs=0.001)
    ponderada = sum(m["pesos"][k] * m["componentes"][k] for k in m["pesos"])
    assert abs(ponderada - m["valor"]) <= 1
    assert m["parcial"] is False and m["ausentes"] == []
    assert len(m["historico"]) == 21
    assert m["historico"][-1]["data"] == "2026-10-05"


def test_snapshot_parcial_sem_ibovespa():
    _gravar(valor=round(80 * 40 / 65 + 40 * 25 / 65), fluxo=80, calma=None, volume=40)
    m = _cliente().get("/api/snapshot").json()["paineis"]["mare"]
    assert m["parcial"] is True
    assert m["ausentes"] == ["calma"]
    assert m["componentes"]["calma"] is None
    assert m["pesos"]["fluxo"] == pytest.approx(40 / 65, abs=0.001)


def test_snapshot_sem_coleta_tem_chave_vazia():
    assert _cliente().get("/api/snapshot").json()["paineis"]["mare"] == {}


def test_painel_mostra_gauge_componentes_e_historico():
    _gravar()
    html = _cliente().get("/").text
    assert "Maré do mercado" in html
    assert "Não é recomendação de compra ou venda" in html
    trecho = html[html.index("Maré do mercado") :]
    assert 'aria-label="Maré do mercado, de 0 a 100: 68, Confiança"' in trecho
    assert trecho.count('class="g-faixa ') == 5
    assert 'class="g-agulha"' in trecho
    for nome in ("Fluxo", "Calma", "Volume"):
        assert nome in trecho
    assert re.search(r'class="comp-valor" width="74"', trecho)
    assert 'class="spark-linha"' in trecho
    assert "há 5 pregões: 56 · Neutro" in trecho
    assert "style=" not in html


def test_painel_parcial_mostra_selo():
    _gravar(valor=65, fluxo=80, calma=None, volume=40)
    html = _cliente().get("/").text
    assert "parcial · sem Calma" in html
    assert "ausente" in html


def test_painel_sem_dado_fica_indisponivel():
    html = _cliente().get("/").text
    trecho = html[html.index("Maré do mercado") :]
    assert "Dado indisponível agora" in trecho[:3000]


def test_mare_fica_ao_lado_do_ibovespa_antes_do_resto():
    _gravar()
    html = _cliente().get("/").text
    titulos = [t for t in re.findall(r"<h2>([^<]+)</h2>", html)]
    assert titulos[:2] == ["Ibovespa hoje", "Maré do mercado"]
