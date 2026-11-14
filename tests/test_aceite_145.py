"""Aceite da spec 145: o gráfico do Ibovespa usa a mesma base do número do dia."""

from __future__ import annotations

import html as html_mod
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.database import IbovespaData, save_ibovespa_data
from app.main import app
from app.services.ibovespa import descrever_serie
from auditoria.auditar import OK, checar_coerencia, extrair_do_snapshot
from devagent.aceite import exigir_spec_done

BRT = timezone(timedelta(hours=-3))
UI_JS = Path(__file__).resolve().parents[1] / "app" / "static" / "ui.js"
client = TestClient(app)

PRIMEIRO = 210000.0
PENULTIMO = 165967.33
ULTIMO = 167627.0


def test_aceite_145_spec_done():
    exigir_spec_done("145")


def _datas() -> list[str]:
    """30 pregões de 23/09/2026 a 05/11/2026 (12/10 e 02/11 não contam)."""
    feriados = {date(2026, 10, 12), date(2026, 11, 2)}
    d, fim, out = date(2026, 9, 23), date(2026, 11, 5), []
    while d <= fim:
        if d.weekday() < 5 and d not in feriados:
            out.append(d.isoformat())
        d += timedelta(days=1)
    assert len(out) == 30
    return out


def _fechamentos() -> list[float]:
    passo = (PRIMEIRO - PENULTIMO) / 28
    meio = [round(PRIMEIRO - passo * i, 2) for i in range(29)]
    meio[-1] = PENULTIMO
    return meio + [ULTIMO]


@pytest.fixture
def relogio(monkeypatch):
    class Relogio(datetime):
        agora: datetime = datetime(2026, 11, 5, 18, 30, tzinfo=BRT)

        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return cls.agora if tz is None else cls.agora.astimezone(tz)

    monkeypatch.setattr("app.main.datetime", Relogio)
    return Relogio


def _gravar(preco: float = ULTIMO) -> None:
    save_ibovespa_data(
        IbovespaData(
            timestamp=datetime(2026, 11, 5, 18, 0, tzinfo=BRT).astimezone(timezone.utc),
            current_price=preco,
            previous_close=PENULTIMO,
            history_json=json.dumps({"dates": _datas(), "closes": _fechamentos()}),
            fonte="yfinance",
        )
    )


def _grafico(pagina: str) -> str:
    m = re.search(r'<div id="grafico-ibovespa".*?>', pagina, re.S)
    assert m, "gráfico do Ibovespa não encontrado na home"
    return m.group(0)


def _atributo(tag: str, nome: str) -> str:
    m = re.search(nome + r"""=(['"])(.*?)\1""", tag, re.S)
    assert m, f"atributo {nome} ausente"
    return html_mod.unescape(m.group(2))


def _legenda(pagina: str) -> str:
    m = re.search(r'<p class="grafico-legenda[^"]*">(.*?)</p>', pagina, re.S)
    assert m, "legenda visível do gráfico ausente"
    return html_mod.unescape(m.group(1))


def test_criterio_1_legenda_30_pregoes_com_datas(relogio):
    _gravar()
    pagina = client.get("/").text
    assert "+1,00%" in pagina  # o card continua com a variação do dia

    legenda = _legenda(pagina)
    assert "30 pregões" in legenda
    assert "23/09/2026" in legenda and "05/11/2026" in legenda
    assert "+1,00%" not in legenda

    aria = _atributo(_grafico(pagina), "aria-label")
    assert "23/09/2026" in aria and "05/11/2026" in aria
    assert "baixa de 20,2%" in aria
    assert "1,00%" not in aria

    # O penúltimo ponto é a base do +1,00%.
    ibov = client.get("/api/snapshot").json()["paineis"]["ibovespa"]
    assert ibov["fechamento_anterior"] == ibov["historico"]["fechamentos"][-2]
    assert ibov["variacao_pct"] == pytest.approx(1.0, abs=0.005)


def test_criterio_2_tooltip_do_ultimo_ponto(relogio):
    _gravar()
    tooltips = json.loads(_atributo(_grafico(client.get("/").text), "data-tooltips"))
    assert len(tooltips) == 30
    ultimo = tooltips[-1]
    assert "05/11/2026" in ultimo
    assert "167.627" in ultimo
    assert "Fechamento anterior 165.967" in ultimo
    assert "+1,00%" in ultimo and "+1.659 pts" in ultimo
    # Pontos anteriores: data e fechamento, sem a variação do dia.
    assert tooltips[0] == "23/09/2026<br><b>210.000</b>"

    js = UI_JS.read_text(encoding="utf-8")
    assert "data-tooltips" in js
    assert "hovertemplate: '%{text}<extra></extra>'" in js


def test_criterio_3_preenchimento_nao_vai_a_zero():
    js = UI_JS.read_text(encoding="utf-8")
    trecho = js.split("graficoIbovespa", 1)[1]
    assert "tozeroy" not in trecho
    assert "fill: 'tonexty'" in trecho
    assert "--baixa-area" in trecho


def test_criterio_4_cor_pelo_sinal_do_periodo(relogio):
    _gravar()
    tag = _grafico(client.get("/").text)
    assert _atributo(tag, "data-periodo-positivo") == "false"
    assert "data-is-positive" not in tag

    js = UI_JS.read_text(encoding="utf-8")
    assert "data-is-positive" not in js
    assert "data-periodo-positivo" in js

    # Janela em alta com dia em queda: linha verde.
    serie = descrever_serie(["2026-11-04", "2026-11-05"], [100.0, 110.0])
    assert serie and serie["periodo_positivo"] is True


def test_criterio_5_coerencia_ultimo_ponto_e_card(relogio):
    _gravar()
    p = extrair_do_snapshot(client.get("/api/snapshot").json())
    assert p is not None
    r = {x.id: x for x in checar_coerencia(p)}
    assert r["ibov.fechamento_anterior_coerente"].status == OK

    _gravar(preco=round(ULTIMO * 1.01, 2))  # 169.303,27: 1% acima do último ponto
    p = extrair_do_snapshot(client.get("/api/snapshot").json())
    assert p is not None
    r = {x.id: x for x in checar_coerencia(p)}
    assert r["ibov.fechamento_anterior_coerente"].status != OK


def test_sem_dois_pontos_nao_desenha():
    assert descrever_serie(["2026-11-05"], [167627.0]) is None
