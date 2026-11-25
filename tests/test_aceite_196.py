"""Spec 196: a ação média do dia contra o Ibovespa."""

import json
import re
from datetime import datetime, timedelta, timezone

import pytest
import respx
from fastapi.testclient import TestClient

from app.collectors.highlights import fetch_yfinance
from app.database import (
    HighlightsData,
    IbovespaData,
    get_latest_highlights_data,
    save_highlights_data,
    save_ibovespa_data,
)
from app.main import app
from app.services.highlights import comparar_com_ibovespa
from devagent.aceite import exigir_spec_done
from tests.test_highlights import SPARK, spark_com_precos

client = TestClient(app)

BRT = timezone(timedelta(hours=-3))
EXEMPLO = {"A": 91.80, "B": 90.90, "C": 89.55, "D": 88.83}
INDICE_ALEM = "o índice foi além da ação média"


@pytest.fixture(autouse=True)
def spec_196_done():
    exigir_spec_done("196")


def _coletar(monkeypatch, precos: dict[str, float]) -> HighlightsData:
    monkeypatch.setattr("app.collectors.highlights.TICKERS", list(precos))
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)
    respx.get(url__regex=SPARK).respond(200, json=spark_com_precos(precos))
    dados = fetch_yfinance()
    assert dados is not None
    return dados


# --- média gravada ---------------------------------------------------------


@respx.mock
def test_coletor_grava_a_media_simples(monkeypatch):
    dados = _coletar(monkeypatch, EXEMPLO)
    assert dados.media_simples_pct is not None
    assert abs(dados.media_simples_pct - 0.30) < 0.001
    assert dados.media_simples_n == 4


@respx.mock
def test_acao_em_revisao_fica_fora_da_media(monkeypatch):
    # A quinta ação sobe 20%; a segunda fonte não confirma, e ela vai para revisão.
    monkeypatch.setattr(
        "app.collectors.highlights.consultar_segunda_fonte",
        lambda *args, **kwargs: None,
    )
    dados = _coletar(monkeypatch, {**EXEMPLO, "E": 108.0})
    assert [a["ticker"] for a in json.loads(dados.em_revisao_json)] == ["E"]
    assert dados.media_simples_pct is not None
    assert abs(dados.media_simples_pct - 0.30) < 0.001
    assert dados.media_simples_n == 4


@respx.mock
def test_media_atravessa_o_banco(monkeypatch):
    save_highlights_data(_coletar(monkeypatch, EXEMPLO))
    lido = get_latest_highlights_data()
    assert lido is not None
    assert lido.media_simples_n == 4
    assert lido.media_simples_pct is not None
    assert abs(lido.media_simples_pct - 0.30) < 0.001


# --- comparação pura -------------------------------------------------------

T0 = datetime(2026, 11, 25, 14, 0, tzinfo=timezone.utc)


def _comparar(media, ibov, minutos=3, valida=True):
    return comparar_com_ibovespa(
        media, 4, ibov, T0 - timedelta(minutes=minutos), T0, valida
    )


def test_comparacao_indice_foi_alem():
    r = _comparar(0.30, 1.00)
    assert r is not None
    assert abs(r["diferenca_pp"] - (-0.70)) < 1e-9
    assert r["leitura"] == INDICE_ALEM
    assert r["diferenca_fmt"] == "−0,70 p.p."
    assert r["media_fmt"] == "+0,30%"
    assert r["ibovespa_fmt"] == "+1,00%"


def test_comparacao_andaram_juntos():
    r = _comparar(1.20, 1.00)
    assert r is not None
    assert r["leitura"] == "índice e ação média andaram juntos"


def test_comparacao_acao_media_foi_alem():
    r = _comparar(1.60, 1.00)
    assert r is not None
    assert r["leitura"] == "a ação média foi além do índice"


def test_limiar_de_meio_ponto_e_inclusivo():
    assert _comparar(0.50, 1.00)["leitura"] == INDICE_ALEM
    assert _comparar(1.50, 1.00)["leitura"] == "a ação média foi além do índice"


@pytest.mark.parametrize(
    "ibov, minutos, valida",
    [
        (1.00, 25, True),  # rodadas diferentes
        (1.00, 3, False),  # Ibovespa em revisão
        (None, 3, False),  # variação indisponível
    ],
)
def test_sem_comparacao_fica_so_a_media(ibov, minutos, valida):
    r = _comparar(0.30, ibov, minutos, valida)
    assert r is not None
    assert r["media_pct"] == 0.30
    assert r["amostra"] == 4
    assert r["diferenca_pp"] is None
    assert r["leitura"] is None
    assert r["ibovespa_pct"] is None


def test_sem_media_nao_ha_linha():
    assert comparar_com_ibovespa(None, None, 1.0, T0, T0, True) is None


# --- tela e snapshot -------------------------------------------------------


def _instantes(afastamento_min: int) -> tuple[datetime, datetime]:
    """(carimbo das maiores altas, carimbo do Ibovespa), no mesmo dia de Brasília."""
    agora = datetime.now(timezone.utc)
    ibov = agora - timedelta(minutes=afastamento_min)
    if ibov.astimezone(BRT).date() != agora.astimezone(BRT).date():
        ibov = agora + timedelta(minutes=afastamento_min)
    return agora, ibov


def _gravar(afastamento_min: int = 3, com_media: bool = True) -> None:
    ts_altas, ts_ibov = _instantes(afastamento_min)
    altas = [
        {"ticker": "A", "price": 91.80, "change_percent": 2.00},
        {"ticker": "B", "price": 90.90, "change_percent": 1.00},
    ]
    baixas = [
        {"ticker": "D", "price": 88.83, "change_percent": -1.30},
        {"ticker": "C", "price": 89.55, "change_percent": -0.50},
    ]
    dados = HighlightsData(
        timestamp=ts_altas,
        highs_json=json.dumps(altas),
        lows_json=json.dumps(baixas),
        fonte="yfinance",
        up_count=2,
        down_count=2,
        total_count=4,
        media_simples_pct=0.30 if com_media else None,
        media_simples_n=4 if com_media else None,
    )
    save_highlights_data(dados)
    if not com_media:
        # Snapshot antigo: o payload gravado antes desta spec não tinha os campos.
        import app.banco

        payload = app.banco.ler_snapshot("maiores_altas_baixas")
        assert payload is not None
        payload = {
            k: v
            for k, v in payload.items()
            if k not in ("media_simples_pct", "media_simples_n")
        }
        app.banco.gravar_snapshot(
            "maiores_altas_baixas",
            ts_altas.astimezone(BRT).date(),
            "ao_vivo",
            "yfinance",
            payload,
        )
        app.banco._snapshot_cache.clear()
    save_ibovespa_data(
        IbovespaData(
            timestamp=ts_ibov,
            current_price=130290.0,
            previous_close=129000.0,
            history_json=json.dumps({"dates": [], "closes": []}),
            fonte="yfinance",
        )
    )


def _card_dispersao(html: str) -> str:
    """Corpo do card Dispersão, depois do texto do método (que cita a ação média)."""
    inicio = html.index("<h2>Dispersão</h2>")
    fim = html.index("</section>", inicio)
    corpo = html.index("</details>", inicio)
    assert corpo < fim
    return html[corpo:fim]


def _texto(trecho: str) -> str:
    """Texto visível do trecho, sem tags, setas de variação e espaços repetidos."""
    sem_tags = re.sub(r"<[^>]+>", " ", trecho)
    sem_setas = re.sub(r"[▲▼■]", " ", sem_tags)
    return re.sub(r"\s+", " ", sem_setas).replace(" )", ")").replace("( ", "(")


def test_tela_mostra_a_comparacao():
    _gravar()
    resp = client.get("/")
    assert resp.status_code == 200
    card = _card_dispersao(resp.text)
    for trecho in ("+0,30%", "+1,00%", "0,70 p.p.", INDICE_ALEM):
        assert trecho in card
    texto = _texto(card)
    assert "Ação média: +0,30% · Ibovespa: +1,00%" in texto
    assert f"Diferença: −0,70 p.p. · {INDICE_ALEM}" in texto


def test_tela_sem_comparacao_mostra_so_a_media():
    _gravar(afastamento_min=25)
    resp = client.get("/")
    assert resp.status_code == 200
    card = _card_dispersao(resp.text)
    assert "Ação média: +0,30% (4 ações)" in _texto(card)
    assert "p.p." not in card


def test_snapshot_antigo_sem_os_campos():
    _gravar(com_media=False)
    lido = get_latest_highlights_data()
    assert lido is not None
    assert lido.media_simples_pct is None
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Ação média" not in _card_dispersao(resp.text)
    snap = client.get("/api/snapshot").json()
    assert snap["paineis"]["altas_baixas"]["acao_media"] is None


def test_snapshot_traz_a_acao_media():
    _gravar()
    snap = client.get("/api/snapshot").json()
    acao = snap["paineis"]["altas_baixas"]["acao_media"]
    assert acao["media_pct"] == pytest.approx(0.30)
    assert acao["amostra"] == 4
    assert acao["ibovespa_pct"] == pytest.approx(1.00)
    assert acao["diferenca_pp"] == pytest.approx(-0.70)
    assert acao["leitura"] == INDICE_ALEM
    # Invariantes de produção da spec.
    assert (
        abs(acao["diferenca_pp"] - (acao["media_pct"] - acao["ibovespa_pct"])) <= 0.01
    )
    ibov = snap["paineis"]["ibovespa"]["variacao_pct"]
    assert abs(acao["ibovespa_pct"] - ibov) <= 0.05
    disp = snap["paineis"]["altas_baixas"]["dispersao"]
    assert disp["em_alta"] + disp["em_baixa"] <= acao["amostra"] <= 30


def test_snapshot_sem_comparacao():
    _gravar(afastamento_min=25)
    acao = client.get("/api/snapshot").json()["paineis"]["altas_baixas"]["acao_media"]
    assert acao["media_pct"] == pytest.approx(0.30)
    assert acao["amostra"] == 4
    assert acao["ibovespa_pct"] is None
    assert acao["diferenca_pp"] is None
    assert acao["leitura"] is None
