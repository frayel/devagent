"""Aceite da spec 158: o Consultor lê as datas e os alvos que o coletor grava.

Sem internet: o banco é o SQLite temporário do `conftest.py`, a série do
`^BVSP` é montada à mão e `calcular_consultor` recebe o histórico por
`monkeypatch`. A data de referência do consenso é passada explicitamente,
para o exemplo da spec não depender do dia em que o teste roda.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from app.consultor import armazenamento, calculador
from app.consultor.armazenamento import ler_data, ler_preco_alvo
from app.consultor.informacoes import construir_informacoes_de
from app.consultor.sintese import calcular_consenso, obter_decisao_final
from app.services.consultor_opinioes import save_opiniao
from devagent.aceite import exigir_spec_done

REFERENCIA = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)

EXEMPLO = [
    {
        "casa": "BTG",
        "recomendacao": "neutro",
        "preco_alvo": "R$ 82",
        "data_materia": "Mon, 02 Nov 2026 10:00:00 +0000",
    },
    {
        "casa": "XP",
        "recomendacao": "neutro",
        "preco_alvo": "",
        "data_materia": "2026-11-03T13:00:00+00:00",
    },
]


def test_aceite_158_spec_done():
    exigir_spec_done("158")


def test_exemplo_de_ponta_a_ponta():
    res = calcular_consenso(EXEMPLO, referencia=REFERENCIA)
    assert res["consenso"] == "neutro"
    assert res["preco_alvo_mediano"] == 82.0
    assert res["faixa"] == (82.0, 82.0)
    assert res["detalhes"]["total"] == 2


def test_ler_data_aceita_rfc822_e_iso_e_nunca_levanta():
    assert ler_data("Mon, 02 Nov 2026 10:00:00 +0000") == datetime(
        2026, 11, 2, 10, 0, tzinfo=timezone.utc
    )
    assert ler_data("2026-11-03T10:00:00-03:00") == datetime(
        2026, 11, 3, 13, 0, tzinfo=timezone.utc
    )
    assert ler_data("2026-11-03T13:00:00Z") == datetime(
        2026, 11, 3, 13, 0, tzinfo=timezone.utc
    )
    for lixo in ("", None, "ontem", "Tue, 99 Foo 2026"):
        assert ler_data(lixo) is None


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("R$ 82", 82.0),
        ("R$ 10,50", 10.5),
        ("7,20", 7.2),
        ("R$ 1.234,50", 1234.5),
        ("82.5", 82.5),
        ("", None),
        ("alvo não informado", None),
        (None, None),
    ],
)
def test_ler_preco_alvo(texto, esperado):
    assert ler_preco_alvo(texto) == esperado


def _gravar_opiniao(ticker, casa, rec, alvo, data):
    save_opiniao(
        guid=f"g-{casa}-{data}",
        ticker=ticker,
        casa=casa,
        recomendacao=rec,
        preco_alvo=alvo,
        resumo="resumo",
        trecho="trecho",
        data_materia=data,
        link="https://exemplo.invalid",
    )


def _datas_gravadas():
    conn, _ = armazenamento.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT data_materia FROM consultor_opinioes ORDER BY id")
        return [r[0] for r in cur.fetchall()]
    finally:
        conn.close()


def test_alvo_ilegivel_nao_derruba_o_consultor(monkeypatch):
    armazenamento.init_db()
    agora = datetime.now(timezone.utc)
    _gravar_opiniao("VALE3", "BTG", "compra", "alvo não informado", agora.isoformat())
    _gravar_opiniao("VALE3", "XP", "compra", "R$ 90", agora.isoformat())
    monkeypatch.setattr(
        calculador, "get_historico_diario", lambda *a, **k: _historico(260)
    )
    res = calculador.calcular_consultor(ignorar_cache=True)
    itens = [i for grupo in res["resultados"].values() for i in grupo]
    vale = next(i for i in itens if i["ticker"] == "VALE3")
    assert vale["consenso"]["consenso"] == "compra"
    assert vale["consenso"]["preco_alvo_mediano"] == 90.0


def test_init_db_migra_rfc822_e_e_idempotente():
    armazenamento.init_db()
    conn, _ = armazenamento.get_connection()
    try:
        cur = conn.cursor()
        for i, data in enumerate(
            [
                "Tue, 03 Nov 2026 16:59:51 +0000",
                "Mon, 02 Nov 2026 10:00:00 +0000",
                "2026-11-01T09:00:00+00:00",
            ]
        ):
            cur.execute(
                "INSERT INTO consultor_opinioes (guid, ticker, casa, recomendacao, preco_alvo, resumo, trecho, data_materia, link, extraida_em) "
                "VALUES (?, 'VALE3', ?, 'compra', '', 'r', 't', ?, 'l', '2026-11-04T00:00:00+00:00')",
                (f"g{i}", f"casa{i}", data),
            )
        cur.execute(
            "INSERT INTO consultor_fila_materias (guid, titulo, descricao, conteudo, data_publicacao, link, tickers_citados, criado_em) "
            "VALUES ('m1', 't', 'd', 'c', 'Tue, 03 Nov 2026 16:59:51 +0000', 'l', '[]', ?)",
            (datetime.now(timezone.utc).isoformat(),),
        )
        conn.commit()
    finally:
        conn.close()

    armazenamento.reset_db_init()
    armazenamento.init_db()
    primeira = _datas_gravadas()
    assert primeira == [
        "2026-11-03T16:59:51+00:00",
        "2026-11-02T10:00:00+00:00",
        "2026-11-01T09:00:00+00:00",
    ]
    materias = armazenamento.get_materias()
    assert materias[0]["data_publicacao"] == "2026-11-03T16:59:51+00:00"

    armazenamento.reset_db_init()
    armazenamento.init_db()
    assert _datas_gravadas() == primeira


def test_save_materia_grava_iso():
    armazenamento.save_materia(
        "m-rfc", "t", "d", "c", "Tue, 03 Nov 2026 16:59:51 +0000", "l", ["VALE3"]
    )
    armazenamento.save_materia("m-lixo", "t", "d", "c", "", "l", ["VALE3"])
    datas = {m["guid"]: m["data_publicacao"] for m in armazenamento.get_materias()}
    assert datas["m-rfc"] == "2026-11-03T16:59:51+00:00"
    assert ler_data(datas["m-lixo"]) is not None


def test_save_opiniao_mesmo_dia_em_formatos_diferentes_grava_uma_linha():
    armazenamento.init_db()
    _gravar_opiniao("VALE3", "BTG", "compra", None, "Tue, 03 Nov 2026 09:00:00 +0000")
    _gravar_opiniao("VALE3", "BTG", "compra", None, "2026-11-03T15:30:00+00:00")
    _gravar_opiniao("VALE3", "BTG", "compra", None, "Tue, 03 Nov 2026 18:45:00 GMT")
    assert _datas_gravadas() == ["2026-11-03T09:00:00+00:00"]


def _historico(n, ultimo=datetime(2026, 11, 3, 13, 0, tzinfo=timezone.utc)):
    fim = int(ultimo.timestamp())
    timestamps = [fim - (n - 1 - i) * 86400 for i in range(n)]
    serie = {
        "timestamp": timestamps,
        "indicators": {
            "quote": [
                {"close": [100.0 + i * 0.1 for i in range(n)], "volume": [1000] * n}
            ]
        },
    }
    return {t: json.dumps(serie) for t in ["^BVSP", "VALE3"]}


def test_informacoes_de_traz_pregao_coleta_e_materia(monkeypatch):
    monkeypatch.setattr(
        calculador, "get_historico_diario", lambda *a, **k: _historico(260)
    )
    monkeypatch.setattr(
        "app.banco.versao_series", lambda ativos: "2026-11-03 21:00:00+00:00"
    )
    dados = calculador.calcular_consultor(ignorar_cache=True)
    dados["opinioes_recentes"] = [
        {"data_materia": "2026-11-02T15:00:00+00:00"},
        {"data_materia": "Sun, 01 Nov 2026 10:00:00 +0000"},
    ]
    info = construir_informacoes_de(dados)
    assert info["sinais_pregao"] == "03/11/2026"
    assert info["sinais_coletado_em"] != "-"
    assert info["opinioes_materia_mais_recente"] == "02/11/2026 12:00"


def _casas(*recs):
    return [
        {
            "casa": f"casa{i}",
            "recomendacao": rec,
            "preco_alvo": "",
            "data_materia": "2026-11-03T13:00:00+00:00",
        }
        for i, rec in enumerate(recs)
    ]


def test_consenso_neutro_compra_e_dividido():
    assert (
        calcular_consenso(_casas(*["neutro"] * 5), referencia=REFERENCIA)["consenso"]
        == "neutro"
    )
    assert (
        calcular_consenso(
            _casas("compra", "compra", "compra", "venda"), referencia=REFERENCIA
        )["consenso"]
        == "compra"
    )
    assert (
        calcular_consenso(
            _casas("compra", "compra", "venda", "venda"), referencia=REFERENCIA
        )["consenso"]
        == "dividido"
    )


def test_neutro_nao_muda_a_decisao_tecnica():
    consenso = {"consenso": "neutro", "detalhes": {"total": 3}}
    for tecnico in ("Comprar", "Vender"):
        dec, frase, _ = obter_decisao_final(
            {"decisao": tecnico, "gatilho": "g", "mm200": 1.0}, consenso, 10.0, 9.0
        )
        assert dec == tecnico
        assert frase == "casas neutras"


def test_novidade_da_correcao_aponta_o_consultor():
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[1]
    entradas = json.loads((raiz / "app" / "novidades.json").read_text("utf-8"))
    alvo = [e for e in entradas if e.get("spec") == "158"]
    assert alvo and alvo[0]["tipo"] == "correcao"
    assert alvo[0]["onde"]["pagina"] == "/consultor"
    assert alvo[0]["onde"]["painel"] == "Opiniões recentes"
