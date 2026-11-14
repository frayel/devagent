"""Aceite da spec 144: a Maré parcial não parece um índice completo."""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.collectors import mare as coletor
from app.database import MareData, get_latest_mare_data, save_mare_data
from app.main import app
from app.services import mare
from devagent.aceite import exigir_spec_done

AGORA = datetime(2026, 10, 6, 20, 0, tzinfo=timezone.utc)  # 17:00 BRT


def test_aceite_144_spec_done():
    exigir_spec_done("144")


def _gravar(valor: int, fluxo, calma, volume) -> None:
    save_mare_data(
        MareData(
            timestamp=datetime(2026, 10, 6, 17, 30, tzinfo=timezone.utc),
            valor=valor,
            fluxo=fluxo,
            calma=calma,
            volume=volume,
            ativos_json="[]",
            historico_json="[]",
            fonte="yfinance",
        )
    )


def _painel() -> str:
    html = TestClient(app).get("/").text
    m = re.search(r"<h2>Maré do mercado</h2>.*?</section>", html, re.S)
    assert m, "painel da Maré não encontrado"
    return m.group(0)


def test_calma_ausente_mostra_cobertura_e_pesos_usados():
    assert mare.indice({"fluxo": 80, "calma": None, "volume": 20})[0] == 57
    _gravar(57, 80.0, None, 20.0)
    painel = _painel()
    assert "parcial" in painel
    assert "Calma" in painel
    assert "parcial · sem Calma · 2 de 3 componentes" in painel
    assert "peso 35%" not in painel
    assert "peso 62%" in painel
    assert "peso 38%" in painel
    assert 'aria-label="Maré do mercado, de 0 a 100: 57, Neutro"' in painel


def test_pesos_visiveis_somam_cem_com_dois_presentes():
    casos = [
        ({"fluxo": 50.0, "calma": 50.0, "volume": None}, [53, 47]),
        ({"fluxo": None, "calma": 50.0, "volume": 50.0}, [58, 42]),
        ({"fluxo": 50.0, "calma": None, "volume": 50.0}, [62, 38]),
    ]
    for comps, esperado in casos:
        dado = MareData(
            timestamp=AGORA,
            valor=50,
            ativos_json="[]",
            historico_json="[]",
            fonte="yfinance",
            **comps,
        )
        pesos = [c["peso"] for c in mare.view(dado)["componentes"]]
        assert [p for p in pesos if p is not None] == esperado
        assert sum(p for p in pesos if p is not None) == 100
        assert pesos.count(None) == 1


def test_so_calma_nao_publica_e_painel_fica_indisponivel(monkeypatch):
    assert mare.indice({"fluxo": None, "calma": 70, "volume": None})[0] is None

    dias, d = [], date(2026, 10, 6)
    while len(dias) < 300:
        if d.weekday() < 5:
            dias.append(d)
        d -= timedelta(days=1)
    dias.reverse()
    ibov, v = {}, 100_000.0
    for i, dia in enumerate(dias):
        v *= 1 + (0.004 + 0.002 * (i % 7) / 6) * (1 if i % 2 else -1)
        ibov[dia] = v

    monkeypatch.setattr(coletor, "buscar_cesta", lambda client: {})
    monkeypatch.setattr(coletor, "buscar_ibov", lambda client: ibov)
    # Só a Calma sai da série: Fluxo e Volume ficam ausentes.
    leitura = mare._Calculadora({}, ibov).leitura(dias[-1], 1.0)
    assert leitura.componentes["calma"] is not None
    assert (
        leitura.componentes["fluxo"] is None and leitura.componentes["volume"] is None
    )
    assert coletor.coletar(AGORA) is None
    assert coletor.collect_and_save() is False
    assert get_latest_mare_data() is None

    painel = _painel()
    assert "Dado indisponível agora" in painel
    assert "g-agulha" not in painel
    assert "Neutro" not in painel


def test_tres_presentes_sem_selo_e_pesos_nominais():
    _gravar(68, 74.2, 61.0, 67.4)
    painel = _painel()
    assert "parcial" not in painel
    for peso in ("peso 40%", "peso 35%", "peso 25%"):
        assert peso in painel


def test_snapshot_publica_pesos_reescalados():
    _gravar(57, 80.0, None, 20.0)
    m = TestClient(app).get("/api/snapshot").json()["paineis"]["mare"]
    assert m["parcial"] is True and m["ausentes"] == ["calma"]
    assert m["pesos"] == {"fluxo": 0.6154, "volume": 0.3846}
    assert abs(sum(m["pesos"].values()) - 1) <= 0.001
    assert json.dumps(m["valor"]) == "57"
