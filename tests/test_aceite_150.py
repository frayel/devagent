"""Aceite da spec 150: radar sem sinal não ocupa um card.

Os 20 radares da classe `alertas` aparecem uma vez cada na aba Alertas: como
card com alertas ou como nome na seção "Sem alertas". Radar sem snapshot é
"indisponível" e coleta velha durante o pregão é "desatualizado"; nenhum dos
dois conta como sem alertas. Sem rede: os getters do banco são trocados por
payloads fixos e o relógio da página é congelado.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient

from app.database import HighlightsData, RadarCongestionamentoData, save_highlights_data
from app.main import app
from app.services.radares import RADARES
from devagent.aceite import exigir_spec_done

client = TestClient(app)

BRT = timezone(timedelta(hours=-3))
# Pregão de segunda, 16/11/2026, 10:45 BRT (exemplo da spec).
AGORA = datetime(2026, 11, 16, 13, 45, tzinfo=timezone.utc)
FRESCO = datetime(2026, 11, 16, 10, 30, tzinfo=BRT)
VELHO = datetime(2026, 11, 16, 10, 0, tzinfo=BRT)

# Onde cada radar lê o banco: (módulo, função), na mesma ordem de RADARES.
GETTERS = {
    "volume_alerts": ("app.services.volume_alerts", "get_latest_volume_alerts_data"),
    "variacao_subita": (
        "app.services.variacao_subita",
        "get_latest_variacao_subita_data",
    ),
    "concentracao_ordens": ("app.database", "get_latest_concentracao_ordens_data"),
    "exaustao_alta": ("app.main", "get_latest_exaustao_alta_data"),
    "exaustao_queda": ("app.main", "get_latest_exaustao_queda_data"),
    "exaustao_tendencia": ("app.main", "get_latest_exaustao_tendencia_data"),
    "radar_absorcao_cruzada": (
        "app.database",
        "get_latest_radar_absorcao_cruzada_data",
    ),
    "liquidez_abertura": ("app.database", "get_latest_liquidez_abertura_data"),
    "radar_congestionamento": (
        "app.database",
        "get_latest_radar_congestionamento_data",
    ),
    "faca_caindo": ("app.services.faca_caindo", "get_latest_faca_caindo_data"),
    "anomalias_spread": ("app.main", "get_latest_radar_anomalias_spread_data"),
    "short_squeeze": (
        "app.services.radar_short_squeeze",
        "get_latest_radar_short_squeeze_data",
    ),
    "falso_rompimento": ("app.database", "get_latest_falso_rompimento_data"),
    "radar_divergencia_volume": (
        "app.database",
        "get_latest_radar_divergencia_volume_data",
    ),
    "esforco_resultado": ("app.database", "get_latest_esforco_resultado_data"),
    "scanner_capitulacao": (
        "app.services.scanner_capitulacao",
        "get_latest_scanner_capitulacao_data",
    ),
    "armadilha_abertura": (
        "app.services.armadilha_abertura",
        "get_latest_armadilha_abertura_data",
    ),
    "compradores_fundo": (
        "app.services.compradores_fundo",
        "get_latest_compradores_fundo_data",
    ),
    "radar_anomalia_fechamento": (
        "app.services.radar_anomalia_fechamento",
        "get_latest_radar_anomalia_fechamento_data",
    ),
    "radar_inflexao": ("app.database", "get_latest_radar_inflexao_data"),
}

NOMES = {chave: nome for chave, nome, _ in RADARES}


@dataclass
class _Snapshot:
    timestamp: datetime
    alertas_json: str = "[]"
    alerts_json: str = "[]"
    fonte: str = "teste"


def _snap(chave: str, timestamp: datetime, alertas: list | None = None):
    corpo = json.dumps(alertas or [])
    if chave == "radar_congestionamento":
        return RadarCongestionamentoData(
            timestamp=timestamp, alertas_json=corpo, fonte="teste"
        )
    return _Snapshot(timestamp=timestamp, alertas_json=corpo, alerts_json=corpo)


@pytest.fixture
def relogio(monkeypatch):
    class Relogio(datetime):
        agora: datetime = AGORA

        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return cls.agora if tz is None else cls.agora.astimezone(tz)

    monkeypatch.setattr("app.main.datetime", Relogio)
    return Relogio


@pytest.fixture
def radares(monkeypatch, relogio):
    """Todos os radares frescos e vazios; o teste troca o que precisar."""
    estado = {chave: _snap(chave, FRESCO) for chave in GETTERS}

    for chave, (modulo, funcao) in GETTERS.items():
        monkeypatch.setattr(f"{modulo}.{funcao}", lambda *a, _c=chave, **k: estado[_c])
    return estado


class _Visivel(HTMLParser):
    """Texto fora de nós `escondido`, e as classes de cada `section.painel`."""

    VAZIOS = {"br", "img", "input", "hr", "meta", "link", "source", "wbr"}

    def __init__(self) -> None:
        super().__init__()
        self.texto: list[str] = []
        self.paineis: list[dict] = []
        self._pilha: list[bool] = []
        self._h2 = False

    def handle_starttag(self, tag, attrs):
        if tag in self.VAZIOS:
            return
        classes = (dict(attrs).get("class") or "").split()
        oculto = "escondido" in classes or (self._pilha and self._pilha[-1])
        self._pilha.append(bool(oculto))
        if tag == "section" and "painel" in classes:
            self.paineis.append({"classes": classes, "titulo": None})
        if tag == "h2":
            self._h2 = True

    def handle_endtag(self, tag):
        if tag in self.VAZIOS:
            return
        if self._pilha:
            self._pilha.pop()
        if tag == "h2":
            self._h2 = False

    def handle_data(self, data):
        if self._h2 and self.paineis and self.paineis[-1]["titulo"] is None:
            self.paineis[-1]["titulo"] = data.strip()
        if not (self._pilha and self._pilha[-1]):
            self.texto.append(data)


def _pagina(url: str = "/") -> tuple[str, _Visivel]:
    resp = client.get(url)
    assert resp.status_code == 200
    p = _Visivel()
    p.feed(resp.text)
    return resp.text, p


def _secao(html: str) -> str:
    m = re.search(r'<section class="[^"]*aviso-vazio[^"]*".*?</section>', html, re.S)
    assert m, "seção Sem alertas ausente"
    return m.group(0)


def _itens(secao: str, classe: str) -> list[str]:
    m = re.search(rf'<ul class="{classe}">(.*?)</ul>', secao, re.S)
    if not m:
        return []
    return [i.strip() for i in re.findall(r"<li>(.*?)</li>", m.group(1), re.S)]


def _card(parser: _Visivel, chave: str) -> dict:
    achados = [p for p in parser.paineis if p["titulo"] == NOMES[chave]]
    assert len(achados) == 1, NOMES[chave]
    return achados[0]


def test_aceite_150_spec_done():
    exigir_spec_done("150")


def test_todos_vazios_viram_nomes_na_secao(radares):
    html, p = _pagina()
    secao = _secao(html)
    assert _itens(secao, "radares-sem-alerta") == [n for _, n, _ in RADARES]
    visivel = " ".join(p.texto)
    assert "Sem alertas" in visivel
    # Nenhuma frase `.vazio` de radar visível.
    for frase in (
        "Nenhuma ação apresentando volume anormal",
        "Nenhum movimento brusco recente",
    ):
        assert frase not in visivel
    for chave in GETTERS:
        card = _card(p, chave)
        assert "radar-vazio" in card["classes"]
        assert "escondido" in card["classes"]
    assert 'aria-pressed="false"' in secao
    assert "Mostrar vazios" in secao


def test_misto_mostra_card_e_secao(radares):
    radares["volume_alerts"] = _snap(
        "volume_alerts", FRESCO, [{"ticker": "PETR4", "ratio": 2.0, "price": 30.0}]
    )
    html, p = _pagina()
    card = _card(p, "volume_alerts")
    assert "escondido" not in card["classes"]
    assert "PETR4" in " ".join(p.texto)
    nomes = _itens(_secao(html), "radares-sem-alerta")
    assert len(nomes) == 19
    assert NOMES["volume_alerts"] not in nomes


def test_vazios_1_mostra_os_cards(radares):
    html, p = _pagina("/?vazios=1")
    for chave in GETTERS:
        card = _card(p, chave)
        assert "radar-vazio" in card["classes"]
        assert "escondido" not in card["classes"]
    secao = _secao(html)
    assert 'aria-pressed="true"' in secao
    assert "Esconder vazios" in secao


def test_botao_preserva_a_data(radares):
    html, _ = _pagina("/?data=2026-11-13")
    secao = _secao(html)
    assert '<input type="hidden" name="data" value="2026-11-13">' in secao
    assert '<button type="submit" name="vazios" value="1"' in secao


def test_radar_none_e_indisponivel(radares):
    radares["faca_caindo"] = None
    html, _ = _pagina()
    secao = _secao(html)
    outros = _itens(secao, "radares-sem-alerta radares-sem-leitura")
    item = [i for i in outros if i.startswith(NOMES["faca_caindo"])]
    assert item == ["Radar de Faca Caindo · indisponível"]
    assert "Nenhum" not in item[0] and "Nenhuma" not in item[0]
    assert NOMES["faca_caindo"] not in _itens(secao, "radares-sem-alerta")


def test_radar_velho_e_desatualizado(radares):
    radares["exaustao_alta"] = _snap("exaustao_alta", VELHO)
    html, _ = _pagina()
    secao = _secao(html)
    assert NOMES["exaustao_alta"] not in _itens(secao, "radares-sem-alerta")
    outros = _itens(secao, "radares-sem-alerta radares-sem-leitura")
    assert "Exaustão de Alta · desatualizado · 10:00" in outros


def test_radar_velho_em_data_historica_nao_e_desatualizado(radares, monkeypatch):
    monkeypatch.setattr(
        "app.main._get_seletor_context",
        _historico(monkeypatch),
    )
    radares["exaustao_alta"] = _snap("exaustao_alta", VELHO)
    html, _ = _pagina()
    assert "desatualizado" not in _secao(html)


def _historico(monkeypatch):
    import app.main as main

    original = main._get_seletor_context

    def ctx(*args, **kwargs):
        c = original(*args, **kwargs)
        return {**c, "is_historical": True}

    return ctx


def test_exemplo_da_spec(radares):
    radares["volume_alerts"] = _snap(
        "volume_alerts",
        FRESCO,
        [
            {"ticker": "PETR4", "ratio": 2.0, "price": 30.0},
            {"ticker": "VALE3", "ratio": 1.8, "price": 60.0},
        ],
    )
    radares["exaustao_alta"] = _snap("exaustao_alta", VELHO)
    radares["faca_caindo"] = None
    html, p = _pagina()
    secao = _secao(html)
    assert len(_itens(secao, "radares-sem-alerta")) == 17
    outros = _itens(secao, "radares-sem-alerta radares-sem-leitura")
    assert outros == [
        "Exaustão de Alta · desatualizado · 10:00",
        "Radar de Faca Caindo · indisponível",
    ]
    # Cada radar aparece uma vez: card visível ou nome na seção.
    visiveis = {
        p_["titulo"]
        for p_ in p.paineis
        if p_["titulo"] in NOMES.values() and "escondido" not in p_["classes"]
    }
    assert visiveis == {"Radar de volume"}
    _, p2 = _pagina("/?vazios=1")
    vazios = [
        x
        for x in p2.paineis
        if "radar-vazio" in x["classes"] and "escondido" not in x["classes"]
    ]
    assert len(vazios) == 17


def test_maiores_altas_continua_visivel(radares):
    highs = [
        {"ticker": f"ACAO{i}", "price": 10.0 + i, "change_percent": 5.0 - i}
        for i in range(5)
    ]
    save_highlights_data(
        HighlightsData(
            timestamp=FRESCO.astimezone(timezone.utc),
            highs_json=json.dumps(highs),
            lows_json="[]",
        )
    )
    _, p = _pagina()
    visivel = " ".join(p.texto)
    for i in range(5):
        assert f"ACAO{i}" in visivel
