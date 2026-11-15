"""Aceite da spec 153: /sistema aponta os candidatos à poda."""

from datetime import date, datetime, timedelta, timezone

import app.banco
from app.services import sistema as s
from devagent.aceite import exigir_spec_done

AGORA = datetime(2026, 11, 15, 6, 0, tzinfo=timezone.utc)  # domingo, 03h BRT
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
PAYLOAD_DIA = {
    "rodadas": {
        "fator_peso_pesado": 28,
        "atrasadas_rally": 28,
        "ibovespa": 28,
        "clima_global": 1,
    },
    "vazias": {"fator_peso_pesado": 15, "atrasadas_rally": 14, "clima_global": 1},
}


def _historico(datas=PREGOES, payload=PAYLOAD_DIA):
    return {d: payload for d in datas}


def test_exemplo_aponta_dois_candidatos():
    exigir_spec_done("153")
    item = s.verificar_candidatos_poda(_historico(), PREGOES)
    assert item.nome == "Candidatos à poda"
    assert item.nivel == "atencao"
    assert item.resumo == (
        "2 painéis vazios em mais da metade das coletas dos últimos 10 pregões"
    )
    assert item.detalhe == (
        "clima_global (10 de 10, 100%), fator_peso_pesado (150 de 280, 54%)"
    )
    assert "atrasadas_rally" not in item.detalhe
    assert "ibovespa" not in item.detalhe


def test_um_candidato_no_singular():
    exigir_spec_done("153")
    payload = {"rodadas": {"a": 2}, "vazias": {"a": 2}}
    item = s.verificar_candidatos_poda(_historico(payload=payload), PREGOES)
    assert item.resumo == (
        "1 painel vazio em mais da metade das coletas dos últimos 10 pregões"
    )
    assert item.detalhe == "a (20 de 20, 100%)"


def test_historico_curto_nao_aponta_ninguem():
    exigir_spec_done("153")
    item = s.verificar_candidatos_poda(_historico(PREGOES[:9]), PREGOES)
    assert item.nivel == "ok"
    assert item.resumo == "histórico de 9 de 10 pregões; o critério precisa de 10"
    assert item.detalhe == ""


def test_historico_vazio():
    exigir_spec_done("153")
    item = s.verificar_candidatos_poda({}, PREGOES)
    assert item.nivel == "ok"
    assert item.resumo == "histórico de 0 de 10 pregões; o critério precisa de 10"


def test_ninguem_acima_da_metade():
    exigir_spec_done("153")
    payload = {"rodadas": {"a": 28, "b": 28}, "vazias": {"a": 14}}
    item = s.verificar_candidatos_poda(_historico(payload=payload), PREGOES)
    assert item.nivel == "ok"
    assert item.resumo == (
        "nenhum painel vazio em mais da metade das coletas dos últimos 10 pregões"
    )


def test_data_fora_dos_pregoes_e_ignorada():
    exigir_spec_done("153")
    historico = _historico()
    historico[date(2026, 11, 14)] = {
        "rodadas": {"atrasadas_rally": 1000, "ibovespa": 1000},
        "vazias": {"atrasadas_rally": 1000, "ibovespa": 1000},
    }
    base = s.verificar_candidatos_poda(_historico(), PREGOES)
    item = s.verificar_candidatos_poda(historico, PREGOES)
    assert (item.nivel, item.resumo, item.detalhe) == (
        base.nivel,
        base.resumo,
        base.detalhe,
    )


def test_ultimos_pregoes_pula_finados():
    exigir_spec_done("153")
    assert s.ultimos_pregoes(AGORA) == PREGOES
    assert date(2026, 11, 2) not in s.ultimos_pregoes(AGORA)


class _CursorEspiao:
    def __init__(self, cursor, chamadas):
        self._cursor = cursor
        self._chamadas = chamadas

    def execute(self, sql, *args):
        self._chamadas.append(sql)
        return self._cursor.execute(sql, *args)

    def __getattr__(self, nome):
        return getattr(self._cursor, nome)


class _ConexaoEspia:
    def __init__(self, conn, chamadas):
        self._conn = conn
        self._chamadas = chamadas

    def cursor(self):
        return _CursorEspiao(self._conn.cursor(), self._chamadas)

    def __getattr__(self, nome):
        return getattr(self._conn, nome)


def test_ler_snapshots_datas_uma_consulta(monkeypatch):
    exigir_spec_done("153")
    d1, d2, d3 = date(2026, 11, 13), date(2026, 11, 12), date(2026, 11, 11)
    for i, d in enumerate((d1, d2, d3)):
        app.banco.gravar_snapshot(
            "instrumentacao", d, "ao_vivo", "agendador", {"rodadas": {"x": i}}
        )
    chamadas: list[str] = []
    original = app.banco.get_connection

    def espiar():
        conn, backend = original()
        return _ConexaoEspia(conn, chamadas), backend

    monkeypatch.setattr(app.banco, "get_connection", espiar)
    res = app.banco.ler_snapshots_datas("instrumentacao", [d1, d3])
    assert res == {d1: {"rodadas": {"x": 0}}, d3: {"rodadas": {"x": 2}}}
    assert all(isinstance(k, date) for k in res)
    selects = [c for c in chamadas if c.lstrip().upper().startswith("SELECT")]
    assert len(selects) == 1


def test_ler_snapshots_datas_lista_vazia_nao_consulta(monkeypatch):
    exigir_spec_done("153")

    def proibido():
        raise AssertionError("não deveria ir ao banco")

    monkeypatch.setattr(app.banco, "get_connection", proibido)
    assert app.banco.ler_snapshots_datas("instrumentacao", []) == {}


def test_ler_snapshots_datas_banco_inacessivel(monkeypatch):
    exigir_spec_done("153")

    def falha():
        raise app.banco.DBInacessivelError("fora")

    monkeypatch.setattr(app.banco, "get_connection", falha)
    assert app.banco.ler_snapshots_datas("instrumentacao", PREGOES) == {}


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


def test_montar_so_mostra_o_item_com_historico():
    exigir_spec_done("153")
    assert "Candidatos à poda" not in _itens_coleta(_montar())
    assert "Candidatos à poda" not in _itens_coleta(_montar(historico_poda=None))
    nomes = _itens_coleta(_montar(historico_poda=_historico()))
    i = nomes.index("Painéis sem dados")
    assert nomes[i + 1] == "Candidatos à poda"
