import json
from datetime import datetime, timezone, timedelta
from app.database import get_connection


def save_materia(
    guid: str,
    titulo: str,
    descricao: str,
    conteudo: str,
    data_publicacao: str,
    link: str,
    tickers_citados: list[str],
) -> None:
    conn = get_connection()
    cursor = conn.cursor()

    agora = datetime.now(timezone.utc).isoformat()
    tickers_json = json.dumps(tickers_citados)

    try:
        cursor.execute(
            """
            INSERT OR IGNORE INTO consultor_fila_materias
            (guid, titulo, descricao, conteudo, data_publicacao, link, tickers_citados, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
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
            "DELETE FROM consultor_fila_materias WHERE criado_em < ?", (limite_dias,)
        )

        cursor.execute(
            """
            DELETE FROM consultor_fila_materias
            WHERE guid NOT IN (
                SELECT guid FROM consultor_fila_materias
                ORDER BY criado_em DESC
                LIMIT 200
            )
            """
        )

        conn.commit()
    finally:
        conn.close()


def get_materias() -> list[dict]:
    conn = get_connection()
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
    conn = get_connection()
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
    conn = get_connection()
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
    conn = get_connection()
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
