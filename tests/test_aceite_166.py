"""Aceite da spec 166: o critério de poda também conta o radar escondido.

Durante o pregão, cada rodada soma `radares_pregao` e, por chave de RADARES,
`escondidos_pregao`; o item "Radares escondidos" de `/sistema` aplica a regra
de metade sobre 10 pregões. Sem rede: SQLite temporário do conftest.
"""

from __future__ import annotations

import importlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

import app.banco
import app.database
from app import agendador
from app.database import gravar_instrumentacao_rodada
from app.services import radares
from app.services import sistema as s
from app.services.radares import RADARES, SNAPSHOT_DO_RADAR
from devagent.aceite import exigir_spec_done

DIA = date(2026, 11, 17)
# 10h15, 10h30, 10h45 e 18h45 BRT (UTC-3) de terça, 17/11/2026.
H1015 = datetime(2026, 11, 17, 13, 15, tzinfo=timezone.utc)
H1030 = datetime(2026, 11, 17, 13, 30, tzinfo=timezone.utc)
H1045 = datetime(2026, 11, 17, 13, 45, tzinfo=timezone.utc)
H1845 = datetime(2026, 11, 17, 21, 45, tzinfo=timezone.utc)

ANTES = {
    "tempos": {"mare": 1.0},
    "rodadas": {"mare": 3},
    "rodadas_pregao": {"mare": 2},
    "radares_pregao": 2,
    "escondidos_pregao": {"faca_caindo": 2, "volume_alerts": 1},
}

PREGOES = [
    date(2026, 11, 13),
    date(2026, 11, 12),
    date(2026, 11, 11),
    date(2026, 11, 10),
    date(2026, 11, 9),
    date(2026, 11, 6),
    date(2026, 11, 5),
    date(2026, 11, 4),
    date(2026, 11, 3),
    date(2026, 10, 30),
]

ESPERADO_ESCONDIDOS = ["faca_caindo", "falso_rompimento", "radar_inflexao"]


@pytest.fixture(autouse=True)
def _spec_done():
    exigir_spec_done("166")


def _exemplo_payloads() -> dict[str, dict]:
    um = json.dumps([{"ticker": "PETR4"}])
    payloads = {c: {f"{campo}_json": um} for c, _n, campo in RADARES}
    payloads["faca_caindo"] = {"alertas_json": "[]"}
    payloads["falso_rompimento"] = {"alertas_json": "não é json"}
    del payloads["radar_inflexao"]
    return payloads


# --- contrato com o código-fonte -------------------------------------------


def test_nome_do_snapshot_e_campo_de_cada_radar_conferem_com_o_database():
    fonte = Path(app.database.__file__).read_text(encoding="utf-8")
    for chave, _nome, campo in RADARES:
        nome = SNAPSHOT_DO_RADAR.get(chave, chave)
        assert re.search(rf'gravar_snapshot\(\s*"{re.escape(nome)}"', fonte), nome
        assert f"{campo}_json" in fonte, campo


# --- escondidos -------------------------------------------------------------


def test_escondidos_do_exemplo():
    assert radares.escondidos(_exemplo_payloads()) == ESPERADO_ESCONDIDOS


def test_sem_payload_todos_escondidos_em_ordem():
    assert radares.escondidos({}) == [c for c, _n, _f in RADARES]


def test_json_falso_e_campo_invalido_escondem():
    payloads = _exemplo_payloads()
    payloads["volume_alerts"] = {"alerts_json": "null"}
    payloads["variacao_subita"] = {"alertas_json": 3}
    payloads["exaustao_alta"] = {}
    payloads["exaustao_queda"] = {"outra": "[1]"}
    assert radares.escondidos(payloads) == [
        "volume_alerts",
        "variacao_subita",
        "exaustao_alta",
        "exaustao_queda",
        *ESPERADO_ESCONDIDOS,
    ]


# --- gravação ---------------------------------------------------------------


def _ler():
    return app.banco.ler_snapshot("instrumentacao", DIA)


def test_gravacao_do_exemplo_campo_a_campo():
    app.banco.gravar_snapshot("instrumentacao", DIA, "ao_vivo", "sistema", ANTES)
    tempos = {"mare": 1.5}

    gravar_instrumentacao_rodada(
        tempos, [], H1015, durante_pregao=True, radares_escondidos=["faca_caindo"]
    )
    p = _ler()
    assert p["radares_pregao"] == 3
    assert p["escondidos_pregao"] == {"faca_caindo": 3, "volume_alerts": 1}
    assert p["rodadas_pregao"] == {"mare": 3}

    gravar_instrumentacao_rodada(
        tempos, [], H1030, durante_pregao=True, radares_escondidos=[]
    )
    p = _ler()
    assert p["radares_pregao"] == 4
    assert p["escondidos_pregao"] == {"faca_caindo": 3, "volume_alerts": 1}
    assert p["rodadas_pregao"] == {"mare": 4}

    gravar_instrumentacao_rodada(
        tempos, [], H1045, durante_pregao=True, radares_escondidos=None
    )
    p = _ler()
    assert p["radares_pregao"] == 4
    assert p["escondidos_pregao"] == {"faca_caindo": 3, "volume_alerts": 1}
    assert p["rodadas_pregao"] == {"mare": 5}

    gravar_instrumentacao_rodada(
        tempos,
        [],
        H1845,
        durante_pregao=False,
        radares_escondidos=["faca_caindo"],
    )
    p = _ler()
    assert p["radares_pregao"] == 4
    assert p["escondidos_pregao"] == {"faca_caindo": 3, "volume_alerts": 1}
    assert p["rodadas_pregao"] == {"mare": 5}


def test_payload_sem_as_chaves_cria_contagem_zerada():
    gravar_instrumentacao_rodada(
        {"mare": 1.5}, [], H1015, durante_pregao=True, radares_escondidos=[]
    )
    p = _ler()
    assert p["radares_pregao"] == 1
    assert p["escondidos_pregao"] == {}


def test_rodada_sem_medidas_nao_grava():
    gravar_instrumentacao_rodada(
        {}, [], H1015, durante_pregao=True, radares_escondidos=["faca_caindo"]
    )
    assert _ler() is None


# --- _coletar ---------------------------------------------------------------


def _relogio(instante: datetime) -> type[datetime]:
    class _Relogio(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return instante if tz is None else instante.astimezone(tz)

    return _Relogio


def _semear_radares():
    for chave, payload in _exemplo_payloads().items():
        nome = SNAPSHOT_DO_RADAR.get(chave, chave)
        app.banco.gravar_snapshot(nome, DIA, "ao_vivo", "teste", payload)


def _rodar_coletar(monkeypatch, instante) -> list[dict]:
    class _Coletor:
        @staticmethod
        def collect_and_save():
            return True

    def importar(nome):
        if nome.rsplit(".", 1)[-1] == "ibovespa":
            return _Coletor
        raise ImportError("coletor fora do teste")

    chamadas: list[dict] = []

    def espiar(tempos, vazias, timestamp, durante_pregao=False, **kw):
        chamadas.append(
            {
                "durante_pregao": durante_pregao,
                "radares_escondidos": kw.get("radares_escondidos"),
            }
        )

    monkeypatch.setattr(importlib, "import_module", importar)
    monkeypatch.setattr(agendador, "datetime", _relogio(instante))
    monkeypatch.setattr(agendador, "_avisar_falha", lambda *a, **k: None)
    monkeypatch.setattr(agendador, "_registrar_erro", lambda *a, **k: None)
    monkeypatch.setattr(app.database, "gravar_instrumentacao_rodada", espiar)
    agendador._coletar()
    return chamadas


def test_coletar_passa_os_escondidos_no_pregao(monkeypatch):
    _semear_radares()
    chamadas = _rodar_coletar(monkeypatch, H1015)
    assert chamadas == [
        {"durante_pregao": True, "radares_escondidos": ESPERADO_ESCONDIDOS}
    ]


def test_coletar_fora_do_pregao_passa_none(monkeypatch):
    _semear_radares()
    chamadas = _rodar_coletar(monkeypatch, H1845)
    assert chamadas == [{"durante_pregao": False, "radares_escondidos": None}]


def test_coletar_com_leitura_falhando_passa_none(monkeypatch):
    _semear_radares()
    original = app.banco.ler_snapshot
    nomes = {SNAPSHOT_DO_RADAR.get(c, c) for c, _n, _f in RADARES}

    def ler(painel, *a, **k):
        if painel in nomes:
            raise RuntimeError("banco fora")
        return original(painel, *a, **k)

    monkeypatch.setattr(app.banco, "ler_snapshot", ler)
    chamadas = _rodar_coletar(monkeypatch, H1015)
    assert chamadas == [{"durante_pregao": True, "radares_escondidos": None}]


# --- critério ---------------------------------------------------------------


def _historico(escondidos, sem=()):
    payload = {"radares_pregao": 30, "escondidos_pregao": escondidos}
    return {d: ({} if d in sem else dict(payload)) for d in PREGOES}


def test_criterio_um_candidato():
    item = s.verificar_radares_escondidos(
        _historico({"faca_caindo": 16, "volume_alerts": 15}), PREGOES
    )
    assert item.nivel == "atencao"
    assert item.resumo == (
        "1 radar escondido em mais da metade das coletas dos últimos 10 pregões"
    )
    assert item.detalhe == "faca_caindo (160 de 300, 53%)"
    assert item.envelhece is False


def test_criterio_dois_candidatos():
    item = s.verificar_radares_escondidos(
        _historico({"faca_caindo": 16, "volume_alerts": 16}), PREGOES
    )
    assert item.nivel == "atencao"
    assert item.resumo == (
        "2 radares escondidos em mais da metade das coletas dos últimos 10 pregões"
    )
    assert item.detalhe == (
        "faca_caindo (160 de 300, 53%), volume_alerts (160 de 300, 53%)"
    )


def test_criterio_historico_incompleto():
    item = s.verificar_radares_escondidos(
        _historico({"faca_caindo": 16}, sem={date(2026, 10, 30)}), PREGOES
    )
    assert item.nivel == "ok"
    assert item.resumo == "histórico de 9 de 10 pregões; o critério precisa de 10"


def test_criterio_sem_candidato():
    item = s.verificar_radares_escondidos(_historico({"faca_caindo": 15}), PREGOES)
    assert item.nivel == "ok"
    assert item.resumo == (
        "nenhum radar escondido em mais da metade das coletas dos últimos 10 pregões"
    )


# --- montar -----------------------------------------------------------------

AGORA = datetime(2026, 11, 16, 15, 0, tzinfo=timezone.utc)


def _montar(**extra):
    return s.montar(
        agora=AGORA,
        inicio=AGORA - timedelta(hours=8),
        remoto={},
        sha_local=None,
        banco={"tipo": "SQLite", "tabelas": 3},
        coleta_ligada=True,
        estado_coleta={},
        intervalo_coleta=timedelta(minutes=15),
        vazios={},
        horas_vazios=3,
        tempos={},
        fontes={},
        pausa_mt5=None,
        prontas=[],
        historico_pregoes=[],
        ambiente={},
        **extra,
    )


def _itens_coleta(estado):
    grupo = next(g for g in estado["grupos"] if g["titulo"] == "Coleta")
    return [i["nome"] for i in grupo["itens"]]


def test_montar_mostra_o_item_depois_dos_candidatos():
    nomes = _itens_coleta(_montar(historico_poda=_historico({})))
    i = nomes.index("Candidatos à poda")
    assert nomes[i + 1] == "Radares escondidos"
    for estado in (_montar(), _montar(historico_poda=None)):
        nomes = _itens_coleta(estado)
        assert "Candidatos à poda" not in nomes
        assert "Radares escondidos" not in nomes
