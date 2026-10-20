import json
from datetime import datetime, timezone, timedelta

import os


def get_armazenamento_tipo() -> str:
    return "postgres" if os.environ.get("DATABASE_URL") else "sqlite_efemero"


def get_armazenamento_conn():
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        import psycopg
        from psycopg.rows import tuple_row

        conn = psycopg.connect(db_url, row_factory=tuple_row)
        return conn
    from app.database import get_connection

    return get_connection()


def translate_query(query: str) -> str:
    if os.environ.get("DATABASE_URL"):
        return query.replace("?", "%s")
    return query


def init_armazenamento_db():
    conn = get_armazenamento_conn()
    cursor = conn.cursor()
    try:
        if os.environ.get("DATABASE_URL"):
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS consultor_recomendacoes (
                    id SERIAL PRIMARY KEY,
                    data_hora TEXT,
                    ticker TEXT,
                    decisao_final TEXT,
                    regra TEXT,
                    consenso TEXT,
                    preco REAL,
                    gatilho TEXT
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS consultor_recomendacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_hora TEXT,
                    ticker TEXT,
                    decisao_final TEXT,
                    regra TEXT,
                    consenso TEXT,
                    preco REAL,
                    gatilho TEXT
                )
            """)
        conn.commit()
    finally:
        conn.close()


def save_recomendacao(
    data_hora: str,
    ticker: str,
    decisao_final: str,
    regra: str,
    consenso: str,
    preco: float,
    gatilho: str,
):
    conn = get_armazenamento_conn()
    cursor = conn.cursor()
    try:
        q = translate_query(
            "INSERT INTO consultor_recomendacoes (data_hora, ticker, decisao_final, regra, consenso, preco, gatilho) VALUES (?, ?, ?, ?, ?, ?, ?)"
        )
        cursor.execute(
            q, (data_hora, ticker, decisao_final, regra, consenso, preco, gatilho)
        )
        conn.commit()
    finally:
        conn.close()


def get_ultima_recomendacao(ticker: str) -> dict | None:
    conn = get_armazenamento_conn()
    cursor = conn.cursor()
    try:
        q = translate_query(
            "SELECT decisao_final FROM consultor_recomendacoes WHERE ticker = ? ORDER BY data_hora DESC LIMIT 1"
        )
        cursor.execute(q, (ticker,))
        row = cursor.fetchone()
        if row:
            return {"decisao_final": row[0]}
        return None
    finally:
        conn.close()


def save_materia(
    guid: str,
    titulo: str,
    descricao: str,
    conteudo: str,
    data_publicacao: str,
    link: str,
    tickers_citados: list[str],
) -> None:
    conn = get_armazenamento_conn()
    cursor = conn.cursor()

    agora = datetime.now(timezone.utc).isoformat()
    tickers_json = json.dumps(tickers_citados)

    try:
        cursor.execute(
            translate_query("""
            INSERT OR IGNORE INTO consultor_fila_materias
            (guid, titulo, descricao, conteudo, data_publicacao, link, tickers_citados, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """),
            (
                guid,
                titulo,
                descricao,
                conteudo,
                data_publicacao,
                link,
                tickers_json,
                agora,
            ),
        )

        limite_dias = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        cursor.execute(
            translate_query("DELETE FROM consultor_fila_materias WHERE criado_em < ?"),
            (limite_dias,),
        )

        cursor.execute(
            translate_query(
                """
            DELETE FROM consultor_fila_materias
            WHERE guid NOT IN (
                SELECT guid FROM consultor_fila_materias
                ORDER BY criado_em DESC
                LIMIT 200
            )
            """
            )
        )

        conn.commit()
    finally:
        conn.close()


def get_materias() -> list[dict]:
    conn = get_armazenamento_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT guid, titulo, descricao, conteudo, data_publicacao, link, tickers_citados, criado_em FROM consultor_fila_materias ORDER BY criado_em DESC"
        )
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append(
                {
                    "guid": row[0],
                    "titulo": row[1],
                    "descricao": row[2],
                    "conteudo": row[3],
                    "data_publicacao": row[4],
                    "link": row[5],
                    "tickers_citados": json.loads(row[6]),
                    "criado_em": row[7],
                }
            )
        return result
    finally:
        conn.close()


def get_opinioes_recentes(limite: int = 20) -> list[dict]:
    conn = get_armazenamento_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, guid, ticker, casa, recomendacao, preco_alvo, resumo, trecho, data_materia, link, extraida_em "
            "FROM consultor_opinioes ORDER BY extraida_em DESC LIMIT ?",
            (limite,),
        )
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append(
                {
                    "id": row[0],
                    "guid": row[1],
                    "ticker": row[2],
                    "casa": row[3],
                    "recomendacao": row[4],
                    "preco_alvo": row[5],
                    "resumo": row[6],
                    "trecho": row[7],
                    "data_materia": row[8],
                    "link": row[9],
                    "extraida_em": row[10],
                }
            )
        return result
    finally:
        conn.close()


def get_opinioes_ativos(dias: int = 30) -> dict:
    conn = get_armazenamento_conn()
    try:
        from datetime import datetime, timezone, timedelta

        limite_data = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()

        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, guid, ticker, casa, recomendacao, preco_alvo, resumo, trecho, data_materia, link, extraida_em "
            "FROM consultor_opinioes WHERE extraida_em >= ? ORDER BY extraida_em DESC",
            (limite_data,),
        )
        rows = cursor.fetchall()
        result: dict[str, list[dict]] = {}
        for row in rows:
            ticker = row[2]
            if ticker not in result:
                result[ticker] = []
            result[ticker].append(
                {
                    "id": row[0],
                    "guid": row[1],
                    "ticker": ticker,
                    "casa": row[3],
                    "recomendacao": row[4],
                    "preco_alvo": row[5],
                    "resumo": row[6],
                    "trecho": row[7],
                    "data_materia": row[8],
                    "link": row[9],
                    "extraida_em": row[10],
                }
            )
        return result
    finally:
        conn.close()


def get_opinioes_status() -> dict:
    conn = get_armazenamento_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status, motivo, desde FROM consultor_opinioes_status LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            return {"status": row[0], "motivo": row[1], "desde": row[2]}
        return {"status": "ok", "motivo": "", "desde": ""}
    finally:
        conn.close()
