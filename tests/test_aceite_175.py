"""Aceite da spec 175: o gráfico da Maré anda no tempo do nível.

Sem internet. A leitura de hoje é gravada como em `tests/test_aceite_174b.py`;
`mare_intradia` e `mare_historico` são snapshots sintéticos no banco
temporário do teste, e o "hoje" BRT é fixado por `mare_servico.hoje_brt`.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import app.banco
from app import calendario
from app.collectors import mare as coletor
from app.database import MareData, get_latest_mare_data, save_mare_data
from app.services import mare as mare_servico
from devagent.aceite import exigir_spec_done

BRT = timezone(timedelta(hours=-3))
HOJE = date(2026, 11, 17)
ONTEM = date(2026, 11, 16)


def test_aceite_175_spec_done():
    exigir_spec_done("175")


@pytest.fixture(autouse=True)
def hoje_fixo(monkeypatch):
    monkeypatch.setattr(mare_servico, "hoje_brt", lambda: HOJE)


def _dado(momento: datetime, valor: int = 55) -> MareData:
    return MareData(
        timestamp=momento.astimezone(timezone.utc),
        valor=valor,
        fluxo=60.0,
        calma=50.0,
        volume=55.0,
        ativos_json="[]",
        historico_json="[]",
        fonte="yfinance",
    )


@pytest.fixture
def com_mare():
    save_mare_data(_dado(datetime(2026, 11, 17, 14, 30, tzinfo=BRT)))


def _intradia(dia: date, pontos: list[tuple[str, int]]) -> None:
    app.banco.gravar_snapshot(
        "mare_intradia",
        dia,
        "ao_vivo",
        "yfinance",
        {
            "data": dia.isoformat(),
            "pontos": [{"hora": h, "valor": v} for h, v in pontos],
        },
    )


def _pregoes_ate(ultimo: date, n: int) -> list[date]:
    dias = [ultimo]
    while len(dias) < n:
        dias.append(calendario.pregao_anterior(dias[-1]))
    return dias[::-1]


def _historico(leituras: list[tuple[date, int]]) -> None:
    app.banco.gravar_snapshot(
        "mare_historico",
        ONTEM,
        "final",
        "yfinance",
        {
            "leituras": [
                {"data": d.isoformat(), "valor": v, "fluxo": v, "calma": v, "volume": v}
                for d, v in leituras
            ],
            "heatmap_ondas": [],
            "heatmap_mare": [],
        },
    )


def _get(caminho: str) -> str:
    from app.main import app as aplicacao

    resposta = TestClient(aplicacao).get(caminho)
    assert resposta.status_code == 200
    return resposta.text


def _card(html: str) -> str:
    m = re.search(
        r'<section class="painel[^"]*\bpainel-mare\b[^"]*">(.*?)</section>', html, re.S
    )
    assert m, "card da Maré não encontrado"
    return m.group(1)


def _aria(card: str) -> str:
    m = re.search(
        r'<div class="spark mare-grafico">\s*<svg[^>]*aria-label="([^"]*)"', card
    )
    assert m, "gráfico da Maré não encontrado"
    return m.group(1)


def _pontos_intradia(dia: date) -> list[dict]:
    payload = app.banco.ler_snapshot("mare_intradia", dia) or {}
    return payload.get("pontos") or []


@pytest.fixture
def coleta(monkeypatch):
    """`collect_and_save` com a coleta trocada por um MareData no momento dado."""
    momento: dict[str, datetime] = {}
    monkeypatch.setattr(coletor, "coletar", lambda: _dado(momento["agora"]))

    def rodar(agora: datetime) -> bool:
        momento["agora"] = agora
        return coletor.collect_and_save()

    return rodar


# --- gravação do ponto intradiário ------------------------------------------


def test_ponto_intradiario_gravado_no_dia_brt(coleta):
    assert coleta(datetime(2026, 11, 17, 14, 30, tzinfo=BRT))
    assert _pontos_intradia(HOJE) == [{"hora": "14:30", "valor": 55}]
    # Mesma HH:MM substitui o ponto.
    assert coleta(datetime(2026, 11, 17, 14, 30, 40, tzinfo=BRT))
    assert len(_pontos_intradia(HOJE)) == 1


@pytest.mark.parametrize(
    "agora",
    [
        datetime(2026, 11, 17, 9, 40, tzinfo=BRT),
        datetime(2026, 11, 17, 18, 30, tzinfo=BRT),
        datetime(2026, 11, 14, 14, 30, tzinfo=BRT),  # sábado
    ],
)
def test_fora_do_pregao_nao_acrescenta(coleta, agora):
    assert coleta(agora)
    assert _pontos_intradia(agora.date()) == []


def test_limites_10h_e_18h15_entram(coleta):
    coleta(datetime(2026, 11, 17, 10, 0, tzinfo=BRT))
    coleta(datetime(2026, 11, 17, 18, 15, tzinfo=BRT))
    assert [p["hora"] for p in _pontos_intradia(HOJE)] == ["10:00", "18:15"]


def test_noite_brt_nao_grava_em_nenhum_dos_dias(coleta):
    # 22:30 BRT de 17/11 é 01:30 UTC de 18/11.
    assert coleta(datetime(2026, 11, 17, 22, 30, tzinfo=BRT))
    assert _pontos_intradia(HOJE) == []
    assert _pontos_intradia(date(2026, 11, 18)) == []


def test_no_maximo_40_pontos(coleta):
    inicio = datetime(2026, 11, 17, 10, 0, tzinfo=BRT)
    pontos = [
        ((inicio + timedelta(minutes=5 * i)).strftime("%H:%M"), 50) for i in range(40)
    ]
    _intradia(HOJE, pontos)
    coleta(datetime(2026, 11, 17, 17, 50, tzinfo=BRT))
    gravados = _pontos_intradia(HOJE)
    assert len(gravados) == 40
    assert "17:50" not in [p["hora"] for p in gravados]


def test_ponto_ordenado_por_hora():
    pontos = mare_servico.acrescentar_ponto(
        [{"hora": "12:00", "valor": 50}], "10:15", 48
    )
    assert [p["hora"] for p in pontos] == ["10:15", "12:00"]


def test_falha_no_intradiario_nao_derruba_a_leitura(coleta, monkeypatch):
    original = app.banco.gravar_snapshot

    def falha(painel, *args, **kwargs):
        if painel == "mare_intradia":
            raise RuntimeError("banco fora")
        return original(painel, *args, **kwargs)

    monkeypatch.setattr(app.banco, "gravar_snapshot", falha)
    assert coleta(datetime(2026, 11, 17, 14, 30, tzinfo=BRT)) is True
    lida = get_latest_mare_data()
    assert lida is not None and lida.valor == 55


# --- Marolas -----------------------------------------------------------------


def test_marolas_desenha_a_curva_de_hoje(com_mare):
    _intradia(HOJE, [("10:15", 48), ("12:00", 50), ("14:30", 55)])
    card = _card(_get("/mare"))
    assert "<span>10:15</span>" in card and "<span>14:30</span>" in card
    assert 'aria-label="Hoje: de 48 (10:15) para 55 (14:30), +7 pontos"' in card
    assert "mín 48 · máx 55" in card
    assert re.search(r'<span class="var alta">\s*▲ \+7 pontos\s*</span>', card)
    assert "há 5 pregões" not in card
    # Marolas não tem linha da média: o gauge é o último ponto.
    assert 'class="mare-media"' not in card


def test_marolas_sem_pontos_hoje_usa_o_pregao_anterior(com_mare):
    _intradia(ONTEM, [("10:15", 50), ("12:00", 52), ("17:00", 49)])
    card = _card(_get("/mare"))
    assert _aria(card).startswith("Pregão de 16/11: de 50 (10:15) para 49 (17:00)")


def test_marolas_com_um_ponto_so_hoje_procura_antes(com_mare):
    _intradia(HOJE, [("10:00", 60)])
    _intradia(ONTEM, [("10:15", 50), ("12:00", 52)])
    assert _aria(_card(_get("/mare"))).startswith("Pregão de 16/11:")


def test_marolas_sem_nenhum_dia_com_curva(com_mare):
    card = _card(_get("/mare"))
    assert "A curva do dia começa na segunda coleta do pregão" in card
    assert "mare-grafico" not in card


# --- Ondas -------------------------------------------------------------------


@pytest.fixture
def ondas(com_mare):
    dias = _pregoes_ate(ONTEM, 21)
    assert dias[0] == date(2026, 10, 16)
    valores = [41] + [50] * 19 + [58]
    _historico(list(zip(dias, valores)))


def test_ondas_desenha_os_21_pregoes(ondas):
    card = _card(_get("/mare?nivel=ondas"))
    assert 'aria-label="21 pregões: de 41 (16/10) para 58 (16/11), +17 pontos"' in card
    pontos = re.search(r'<polyline class="spark-linha" points="([^"]*)"', card)
    assert pontos is not None
    lista = pontos.group(1).split()
    assert len(lista) == 21
    assert lista[0] == "0.0,44.0" and lista[-1] == "200.0,4.0"
    assert re.search(r'class="mare-media"[^>]*y1="22.8"', card)
    assert "<span>16/10</span>" in card and "<span>16/11</span>" in card
    assert "mín 41 · máx 58" in card


def test_ondas_com_18_leituras(com_mare):
    dias = _pregoes_ate(ONTEM, 18)
    _historico([(d, 50) for d in dias[:-1]] + [(dias[-1], 56)])
    aria = _aria(_card(_get("/mare?nivel=ondas")))
    assert aria.startswith("18 pregões: de 50 (")


def test_fragmento_traz_o_grafico_de_ondas(ondas):
    html = _get("/mare/card?nivel=ondas")
    assert "<html" not in html
    assert _aria(_card(html)).startswith("21 pregões:")


def test_ondas_em_formacao_sem_grafico(com_mare):
    dias = _pregoes_ate(ONTEM, 10)
    _historico([(d, 50) for d in dias])
    card = _card(_get("/mare?nivel=ondas"))
    assert "mare-grafico" not in card
    assert "em formação" in card


# --- Maré --------------------------------------------------------------------


def test_mare_um_ponto_por_mes(com_mare):
    dias = _pregoes_ate(ONTEM, 252)
    assert dias[0] == date(2025, 11, 10)
    _historico([(d, 50) for d in dias])
    card = _card(_get("/mare?nivel=mare"))
    aria = _aria(card)
    assert aria.startswith("13 meses: de 50 (nov/25) para 50 (nov/26), estável")
    pontos = re.search(r'<polyline class="spark-linha" points="([^"]*)"', card)
    assert pontos is not None and len(pontos.group(1).split()) == 13
    assert "<span>nov/25</span>" in card and "<span>nov/26</span>" in card
    assert re.search(r'<span class="var neutra">\s*■ estável\s*</span>', card)


def test_mare_borda_com_menos_de_5_leituras_sai(com_mare):
    dias = [d for d in _pregoes_ate(ONTEM, 252) if d >= date(2025, 11, 26)]
    assert len([d for d in dias if d.month == 11 and d.year == 2025]) == 3
    _historico([(d, 50) for d in dias])
    aria = _aria(_card(_get("/mare?nivel=mare")))
    assert aria.startswith("12 meses: de 50 (dez/25)")


def test_media_mensal():
    leituras = [{"data": f"2026-11-{d:02d}", "valor": 50} for d in range(3, 11)]
    leituras += [
        {"data": "2026-11-11", "valor": 55},
        {"data": "2026-11-12", "valor": 55},
    ]
    assert mare_servico.serie_mensal(leituras) == [("nov/26", 51)]


# --- queda e variação zero ---------------------------------------------------


def test_queda_usa_o_sinal_de_menos_e_a_classe_baixa(com_mare):
    _intradia(HOJE, [("10:15", 55), ("14:30", 49)])
    card = _card(_get("/mare"))
    assert _aria(card) == "Hoje: de 55 (10:15) para 49 (14:30), −6 pontos"
    assert re.search(r'<span class="var baixa">\s*▼ −6 pontos\s*</span>', card)


def test_variacao_zero_e_estavel(com_mare):
    _intradia(HOJE, [("10:15", 50), ("14:30", 50)])
    card = _card(_get("/mare"))
    assert _aria(card) == "Hoje: de 50 (10:15) para 50 (14:30), estável"
    assert re.search(r'<span class="var neutra">\s*■ estável\s*</span>', card)


# --- /api/snapshot ------------------------------------------------------------


def test_snapshot_traz_a_curva_do_dia(com_mare):
    from app.main import app as aplicacao

    _intradia(HOJE, [("10:15", 48), ("14:30", 55)])
    m = TestClient(aplicacao).get("/api/snapshot").json()["paineis"]["mare"]
    assert m["intradia"] == {
        "data": "2026-11-17",
        "pontos": [{"hora": "10:15", "valor": 48}, {"hora": "14:30", "valor": 55}],
    }


def test_snapshot_sem_curva_e_null(com_mare):
    from app.main import app as aplicacao

    m = TestClient(aplicacao).get("/api/snapshot").json()["paineis"]["mare"]
    assert m["intradia"] is None


def test_build_sparkline_sem_referencia_nao_muda():
    from app.services.sparkline import build_sparkline

    saida = build_sparkline([1.0, 2.0, 3.0])
    assert saida == {
        "pontos": "0.0,44.0 100.0,24.0 200.0,4.0",
        "ultimo_x": 200,
        "ultimo_y": 4.0,
    }
    assert json.dumps(saida)


# --- data passada --------------------------------------------------------------


@pytest.fixture
def calendario_fixo(monkeypatch):
    class Mercado:
        def mercado_aberto(self, dt):
            return False

        def pregao_corrente(self, dt):
            return HOJE

        def ultimo_pregao_fechado(self, dt):
            return HOJE

    monkeypatch.setattr("app.main.calendario", Mercado())
    monkeypatch.setattr(
        "app.main.obter_pregoes_disponiveis",
        lambda *a, **k: [HOJE.isoformat(), ONTEM.isoformat()],
    )


def test_data_passada_usa_a_curva_daquela_data(com_mare, calendario_fixo):
    save_mare_data(_dado(datetime(2026, 11, 16, 14, 30, tzinfo=BRT), valor=49))
    _intradia(ONTEM, [("10:15", 50), ("17:00", 49)])
    _intradia(HOJE, [("10:15", 40), ("14:30", 60)])
    card = _card(_get("/mare/card?data=2026-11-16"))
    assert _aria(card) == "Pregão de 16/11: de 50 (10:15) para 49 (17:00), −1 pontos"


def test_data_passada_sem_curva_fica_sem_grafico_e_sem_frase(com_mare, calendario_fixo):
    save_mare_data(_dado(datetime(2026, 11, 16, 14, 30, tzinfo=BRT), valor=49))
    card = _card(_get("/mare/card?data=2026-11-16"))
    assert "mare-grafico" not in card
    assert "A curva do dia começa" not in card
