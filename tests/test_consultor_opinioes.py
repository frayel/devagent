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


def test_acceptance_xml_feed(monkeypatch):
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
        <channel>
            <item><title>BBAS3 compra recomendada</title><link>http://l1</link><guid>g1</guid><description>A</description><content:encoded>A</content:encoded><pubDate>D</pubDate></item>
            <item><title>Apenas notícia sobre Vale</title><link>http://l2</link><guid>g2</guid><description>Vale divulga</description><content:encoded>A</content:encoded><pubDate>D</pubDate></item>
            <item><title>Recomendação de empresa desconhecida</title><link>http://l3</link><guid>g3</guid><description>Compra XYZ</description><content:encoded>A</content:encoded><pubDate>D</pubDate></item>
            <item><title>PETR4 elevou recomendação</title><link>http://l4</link><guid>g4</guid><description>B</description><content:encoded>B</content:encoded><pubDate>D</pubDate></item>
            <item><title>Outra 5</title><link>http://l5</link><guid>g5</guid><description>C</description><content:encoded>C</content:encoded><pubDate>D</pubDate></item>
            <item><title>Outra 6</title><link>http://l6</link><guid>g6</guid><description>C</description><content:encoded>C</content:encoded><pubDate>D</pubDate></item>
            <item><title>Outra 7</title><link>http://l7</link><guid>g7</guid><description>C</description><content:encoded>C</content:encoded><pubDate>D</pubDate></item>
            <item><title>Outra 8</title><link>http://l8</link><guid>g8</guid><description>C</description><content:encoded>C</content:encoded><pubDate>D</pubDate></item>
            <item><title>Outra 9</title><link>http://l9</link><guid>g9</guid><description>C</description><content:encoded>C</content:encoded><pubDate>D</pubDate></item>
            <item><title>Outra 10</title><link>http://l10</link><guid>g10</guid><description>C</description><content:encoded>C</content:encoded><pubDate>D</pubDate></item>
        </channel>
    </rss>
    """

    def mock_fetch(url, *args, **kwargs):
        return xml if "moneytimes" in url else None

    monkeypatch.setattr(
        "app.collectors.consultor_opinioes.fetch_with_retry", mock_fetch
    )

    conn = get_connection()
    c_db = conn.cursor()
    c_db.execute("DELETE FROM consultor_fila_materias")
    conn.commit()
    conn.close()

    collect_and_save()

    materias = get_materias()

    assert len(materias) == 2
    titulos = [m["titulo"] for m in materias]
    assert "BBAS3 compra recomendada" in titulos
    assert "PETR4 elevou recomendação" in titulos
