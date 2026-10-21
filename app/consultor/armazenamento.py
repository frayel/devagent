import json
from datetime import datetime, timezone, timedelta

from app.banco import get_connection


def init_db():
    conn, backend = get_connection()
    try:
        if backend == "postgres":
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS consultor_opinioes (
                        id SERIAL PRIMARY KEY,
                        guid TEXT NOT NULL,
                        ticker TEXT NOT NULL,
                        casa TEXT NOT NULL,
                        recomendacao TEXT NOT NULL,
                        preco_alvo TEXT,
                        resumo TEXT NOT NULL,
                        trecho TEXT NOT NULL,
                        data_materia TEXT NOT NULL,
                        link TEXT NOT NULL,
                        extraida_em TEXT DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE (ticker, casa, recomendacao, data_materia)
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS consultor_opinioes_status (
                        id SERIAL PRIMARY KEY,
                        status TEXT NOT NULL,
                        motivo TEXT,
                        desde TEXT NOT NULL
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS consultor_recomendacoes (
                        id SERIAL PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        ticker TEXT NOT NULL,
                        decisao_final TEXT NOT NULL,
                        regra_tecnica TEXT NOT NULL,
                        consenso TEXT,
                        preco REAL NOT NULL,
                        gatilho TEXT NOT NULL
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS consultor_fechamentos (
                        id SERIAL PRIMARY KEY,
                        data_pregao TEXT NOT NULL,
                        ticker TEXT NOT NULL,
                        preco_fechamento REAL NOT NULL,
                        UNIQUE (data_pregao, ticker)
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS consultor_fila_materias (
                        guid TEXT PRIMARY KEY,
                        titulo TEXT NOT NULL,
                        descricao TEXT NOT NULL,
                        conteudo TEXT NOT NULL,
                        data_publicacao TEXT NOT NULL,
                        link TEXT NOT NULL,
                        tickers_citados TEXT NOT NULL,
                        criado_em TEXT DEFAULT CURRENT_TIMESTAMP
                    );
                """)
            conn.commit()
            conn.close()
        else:
            cursor = conn.cursor()
            # SQLite tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS consultor_opinioes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guid TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    casa TEXT NOT NULL,
                    recomendacao TEXT NOT NULL,
                    preco_alvo TEXT,
                    resumo TEXT NOT NULL,
                    trecho TEXT NOT NULL,
                    data_materia TEXT NOT NULL,
                    link TEXT NOT NULL,
                    extraida_em TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ticker, casa, recomendacao, data_materia)
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS consultor_opinioes_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT NOT NULL,
                    motivo TEXT,
                    desde TEXT NOT NULL
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS consultor_recomendacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    decisao_final TEXT NOT NULL,
                    regra_tecnica TEXT NOT NULL,
                    consenso TEXT,
                    preco REAL NOT NULL,
                    gatilho TEXT NOT NULL
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS consultor_fechamentos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_pregao TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    preco_fechamento REAL NOT NULL,
                    UNIQUE(data_pregao, ticker)
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS consultor_fila_materias (
                    guid TEXT PRIMARY KEY,
                    titulo TEXT NOT NULL,
                    descricao TEXT NOT NULL,
                    conteudo TEXT NOT NULL,
                    data_publicacao TEXT NOT NULL,
                    link TEXT NOT NULL,
                    tickers_citados TEXT NOT NULL,
                    criado_em TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            conn.close()
    except Exception:
        pass


def save_materia(
    guid: str,
    titulo: str,
    descricao: str,
    conteudo: str,
    data_publicacao: str,
    link: str,
    tickers_citados: list[str],
) -> None:
    init_db()
    conn, backend = get_connection()
    agora = datetime.now(timezone.utc).isoformat()
    tickers_json = json.dumps(tickers_citados)

    try:
        if backend == "postgres":
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO consultor_fila_materias
                    (guid, titulo, descricao, conteudo, data_publicacao, link, tickers_citados, criado_em)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (guid) DO NOTHING
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
                limite_dias = (
                    datetime.now(timezone.utc) - timedelta(days=3)
                ).isoformat()
                cursor.execute(
                    "DELETE FROM consultor_fila_materias WHERE criado_em < %s",
                    (limite_dias,),
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
        else:
            cursor = conn.cursor()
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
                "DELETE FROM consultor_fila_materias WHERE criado_em < ?",
                (limite_dias,),
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
    init_db()
    conn, backend = get_connection()
    try:
        if backend == "postgres":
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT guid, titulo, descricao, conteudo, data_publicacao, link, tickers_citados, criado_em FROM consultor_fila_materias ORDER BY criado_em DESC"
                )
                rows = cursor.fetchall()
        else:
            cursor = conn.cursor()
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
    init_db()
    conn, backend = get_connection()
    try:
        if backend == "postgres":
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, guid, ticker, casa, recomendacao, preco_alvo, resumo, trecho, data_materia, link, extraida_em "
                    "FROM consultor_opinioes ORDER BY extraida_em DESC LIMIT %s",
                    (limite,),
                )
                rows = cursor.fetchall()
        else:
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
    init_db()
    conn, backend = get_connection()
    try:
        limite_data = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
        if backend == "postgres":
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, guid, ticker, casa, recomendacao, preco_alvo, resumo, trecho, data_materia, link, extraida_em "
                    "FROM consultor_opinioes WHERE extraida_em >= %s ORDER BY extraida_em DESC",
                    (limite_data,),
                )
                rows = cursor.fetchall()
        else:
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
    init_db()
    conn, backend = get_connection()
    try:
        if backend == "postgres":
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT status, motivo, desde FROM consultor_opinioes_status LIMIT 1"
                )
                row = cursor.fetchone()
        else:
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


def save_recomendacoes(resultados_list: list[dict]):
    init_db()
    if not resultados_list:
        return

    conn, backend = get_connection()
    try:
        if backend == "postgres":
            with conn.cursor() as cursor:
                for res in resultados_list:
                    cursor.execute(
                        "SELECT decisao_final, regra_tecnica FROM consultor_recomendacoes WHERE ticker = %s ORDER BY timestamp DESC LIMIT 1",
                        (res["ticker"],),
                    )
                    last = cursor.fetchone()
                    if last is None or (
                        last[0] != res["decisao"] or last[1] != res["regra"]
                    ):
                        cursor.execute(
                            "INSERT INTO consultor_recomendacoes (timestamp, ticker, decisao_final, regra_tecnica, consenso, preco, gatilho) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                            (
                                res["timestamp"],
                                res["ticker"],
                                res["decisao"],
                                res["regra"],
                                res["consenso"],
                                res["preco"],
                                res["gatilho"],
                            ),
                        )
            conn.commit()
        else:
            cursor = conn.cursor()
            for res in resultados_list:
                cursor.execute(
                    "SELECT decisao_final, regra_tecnica FROM consultor_recomendacoes WHERE ticker = ? ORDER BY timestamp DESC LIMIT 1",
                    (res["ticker"],),
                )
                last = cursor.fetchone()
                if last is None or (
                    last[0] != res["decisao"] or last[1] != res["regra"]
                ):
                    cursor.execute(
                        "INSERT INTO consultor_recomendacoes (timestamp, ticker, decisao_final, regra_tecnica, consenso, preco, gatilho) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            res["timestamp"],
                            res["ticker"],
                            res["decisao"],
                            res["regra"],
                            res["consenso"],
                            res["preco"],
                            res["gatilho"],
                        ),
                    )
            conn.commit()
    finally:
        conn.close()


def save_fechamentos(resultados_list: list[dict]):
    init_db()
    if not resultados_list:
        return

    # Only run after 18h BRT
    now_brt = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-3)))
    if now_brt.hour < 18:
        return

    data_pregao = now_brt.strftime("%Y-%m-%d")

    conn, backend = get_connection()
    try:
        if backend == "postgres":
            with conn.cursor() as cursor:
                for res in resultados_list:
                    cursor.execute(
                        "INSERT INTO consultor_fechamentos (data_pregao, ticker, preco_fechamento) VALUES (%s, %s, %s) ON CONFLICT (data_pregao, ticker) DO NOTHING",
                        (data_pregao, res["ticker"], res["preco"]),
                    )
            conn.commit()
        else:
            cursor = conn.cursor()
            for res in resultados_list:
                cursor.execute(
                    "INSERT OR IGNORE INTO consultor_fechamentos (data_pregao, ticker, preco_fechamento) VALUES (?, ?, ?)",
                    (data_pregao, res["ticker"], res["preco"]),
                )
            conn.commit()
    finally:
        conn.close()
