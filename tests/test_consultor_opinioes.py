from app.consultor.pre_filtro import filtrar_materia
from app.collectors.consultor_opinioes import parse_feed, collect_and_save
from app.consultor.armazenamento import save_materia, get_materias
from app.database import get_connection
from datetime import datetime, timezone, timedelta


def test_filtrar_materia_match():
    tickers = filtrar_materia(
        "Itaú recomenda compra de Petrobras", "A PETR4 deve subir", ""
    )
    assert "PETR3" in tickers or "PETR4" in tickers or "ITUB4" in tickers


def test_filtrar_materia_no_match_opinion():
    tickers = filtrar_materia("Petrobras divulga balanço", "Lucro da PETR4", "")
    assert tickers == []


def test_filtrar_materia_no_match_ticker():
    tickers = filtrar_materia("Banco recomenda compra de empresa X", "", "")
    assert tickers == []


def test_armazenamento_limite_e_descarte():
    agora = datetime.now(timezone.utc)
    # Insert 205 materias
    for i in range(205):
        save_materia(f"guid_{i}", f"titulo {i}", "", "", "", "", ["PETR4"])

    materias = get_materias()
    assert len(materias) == 200

    # modify one to be old
    conn = get_connection()
    cursor = conn.cursor()
    antigo = (agora - timedelta(days=4)).isoformat()
    cursor.execute(
        "UPDATE consultor_fila_materias SET criado_em = ? WHERE guid = 'guid_199'",
        (antigo,),
    )
    conn.commit()
    conn.close()

    save_materia("guid_novo", "titulo novo", "", "", "", "", ["VALE3"])
    materias = get_materias()
    assert len(materias) <= 200
    assert not any(m["guid"] == "guid_199" for m in materias)


def test_parse_feed():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
        <channel>
            <item>
                <title>BBAS3 compra recomendada</title>
                <link>http://link1</link>
                <guid>guid1</guid>
                <description>desc</description>
                <content:encoded>conteudo</content:encoded>
                <pubDate>Thu, 01 Jan 2026</pubDate>
            </item>
        </channel>
    </rss>
    """
    res = parse_feed(xml)
    assert len(res) == 1
    assert res[0]["titulo"] == "BBAS3 compra recomendada"
    assert res[0]["conteudo"] == "conteudo"


def test_collect_and_save_errors(monkeypatch):
    def mock_fetch(url):
        return None

    monkeypatch.setattr(
        "app.collectors.consultor_opinioes.fetch_with_retry", mock_fetch
    )
    # Should not raise exception
    res = collect_and_save()
    assert res is False
