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
