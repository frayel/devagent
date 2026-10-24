import json
from datetime import datetime, timezone, timedelta

from app.banco import get_connection


def sql_para(backend: str, sqlite_sql: str) -> str:
    """Substitui `?` por `%s` se for postgres, senao mantem."""
    if backend == "postgres":
        return sqlite_sql.replace("?", "%s")
    return sqlite_sql


_consultor_db_initialized = False


def reset_db_init():
    global _consultor_db_initialized
    _consultor_db_initialized = False


def init_db():
    global _consultor_db_initialized
    if _consultor_db_initialized:
        return
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
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_consultor_opinioes_extraida_em ON consultor_opinioes(extraida_em DESC);"
                )
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS consultor_opinioes_status (
                        id SERIAL PRIMARY KEY,
                        status TEXT NOT NULL,
                        motivo TEXT,
                        desde TEXT NOT NULL,
                        ultima_extracao_em TEXT,
                        materias_processadas INTEGER DEFAULT 0,
                        opinioes_gravadas INTEGER DEFAULT 0,
                        descartadas INTEGER DEFAULT 0
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
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_consultor_recomendacoes_ticker_timestamp ON consultor_recomendacoes(ticker, timestamp DESC);"
                )
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
                        criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
                        processada INTEGER NOT NULL DEFAULT 0
                    );
                """)
                cursor.execute(
                    "ALTER TABLE consultor_fila_materias ADD COLUMN IF NOT EXISTS processada INTEGER NOT NULL DEFAULT 0;"
                )
                cursor.execute(
                    "ALTER TABLE consultor_opinioes_status ADD COLUMN IF NOT EXISTS ultima_extracao_em TEXT;"
                )
                cursor.execute(
                    "ALTER TABLE consultor_opinioes_status ADD COLUMN IF NOT EXISTS materias_processadas INTEGER DEFAULT 0;"
                )
                cursor.execute(
                    "ALTER TABLE consultor_opinioes_status ADD COLUMN IF NOT EXISTS opinioes_gravadas INTEGER DEFAULT 0;"
                )
                cursor.execute(
                    "ALTER TABLE consultor_opinioes_status ADD COLUMN IF NOT EXISTS descartadas INTEGER DEFAULT 0;"
                )
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS consultor_llm_uso (
                        data DATE PRIMARY KEY,
                        chamadas INTEGER NOT NULL DEFAULT 0
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
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_consultor_opinioes_extraida_em ON consultor_opinioes(extraida_em DESC)"
            )
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS consultor_opinioes_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT NOT NULL,
                    motivo TEXT,
                    desde TEXT NOT NULL,
                    ultima_extracao_em TEXT,
                    materias_processadas INTEGER DEFAULT 0,
                    opinioes_gravadas INTEGER DEFAULT 0,
                    descartadas INTEGER DEFAULT 0
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
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_consultor_recomendacoes_ticker_timestamp ON consultor_recomendacoes(ticker, timestamp DESC)"
            )
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
                    criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
                    processada INTEGER NOT NULL DEFAULT 0
                );
            """)
            try:
                cursor.execute(
                    "ALTER TABLE consultor_fila_materias ADD COLUMN processada INTEGER DEFAULT 0"
                )
            except Exception:
                pass
            try:
                cursor.execute(
                    "ALTER TABLE consultor_opinioes_status ADD COLUMN ultima_extracao_em TEXT"
                )
            except Exception:
                pass
            try:
                cursor.execute(
                    "ALTER TABLE consultor_opinioes_status ADD COLUMN materias_processadas INTEGER DEFAULT 0"
                )
            except Exception:
                pass
            try:
                cursor.execute(
                    "ALTER TABLE consultor_opinioes_status ADD COLUMN opinioes_gravadas INTEGER DEFAULT 0"
                )
            except Exception:
                pass
            try:
                cursor.execute(
                    "ALTER TABLE consultor_opinioes_status ADD COLUMN descartadas INTEGER DEFAULT 0"
                )
            except Exception:
                pass
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
        _consultor_db_initialized = True
    finally:
        conn.close()


def get_materias() -> list[dict]:
    init_db()
    conn, backend = get_connection()
    try:
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
        cursor = conn.cursor()
        cursor.execute(
            sql_para(
                backend,
                "SELECT id, guid, ticker, casa, recomendacao, preco_alvo, resumo, trecho, data_materia, link, extraida_em "
                "FROM consultor_opinioes ORDER BY extraida_em DESC LIMIT ?",
            ),
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
        cursor = conn.cursor()
        cursor.execute(
            sql_para(
                backend,
                "SELECT id, guid, ticker, casa, recomendacao, preco_alvo, resumo, trecho, data_materia, link, extraida_em "
                "FROM consultor_opinioes WHERE extraida_em >= ? ORDER BY extraida_em DESC",
            ),
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
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status, motivo, desde, ultima_extracao_em, materias_processadas, opinioes_gravadas, descartadas FROM consultor_opinioes_status LIMIT 1"
        )
        row = cursor.fetchone()

        if row:
            return {
                "status": row[0],
                "motivo": row[1],
                "desde": row[2],
                "ultima_extracao_em": row[3] or "",
                "materias_processadas": row[4] or 0,
                "opinioes_gravadas": row[5] or 0,
                "descartadas": row[6] or 0,
            }
        return {
            "status": "ok",
            "motivo": "",
            "desde": "",
            "ultima_extracao_em": "",
            "materias_processadas": 0,
            "opinioes_gravadas": 0,
            "descartadas": 0,
        }
    finally:
        conn.close()


def save_recomendacoes(resultados_list: list[dict]):
    init_db()
    if not resultados_list:
        return

    conn, backend = get_connection()
    try:
        cursor = conn.cursor()
        for res in resultados_list:
            cursor.execute(
                sql_para(
                    backend,
                    "SELECT decisao_final, regra_tecnica FROM consultor_recomendacoes WHERE ticker = ? ORDER BY timestamp DESC LIMIT 1",
                ),
                (res["ticker"],),
            )
            last = cursor.fetchone()
            if last is None or (last[0] != res["decisao"] or last[1] != res["regra"]):
                cursor.execute(
                    sql_para(
                        backend,
                        "INSERT INTO consultor_recomendacoes (timestamp, ticker, decisao_final, regra_tecnica, consenso, preco, gatilho) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ),
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
        cursor = conn.cursor()
        for res in resultados_list:
            if backend == "postgres":
                cursor.execute(
                    "INSERT INTO consultor_fechamentos (data_pregao, ticker, preco_fechamento) VALUES (%s, %s, %s) ON CONFLICT (data_pregao, ticker) DO NOTHING",
                    (data_pregao, res["ticker"], res["preco"]),
                )
            else:
                cursor.execute(
                    "INSERT OR IGNORE INTO consultor_fechamentos (data_pregao, ticker, preco_fechamento) VALUES (?, ?, ?)",
                    (data_pregao, res["ticker"], res["preco"]),
                )
        conn.commit()
    finally:
        conn.close()


def get_recomendacoes(data_referencia: str) -> list[dict]:
    init_db()
    conn, backend = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            sql_para(
                backend,
                "SELECT ticker, timestamp, decisao_final, regra_tecnica, consenso, preco, gatilho FROM consultor_recomendacoes WHERE timestamp LIKE ? ORDER BY ticker ASC",
            ),
            (f"{data_referencia}%",),
        )
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append(
                {
                    "ticker": row[0],
                    "timestamp": row[1],
                    "decisao": row[2],
                    "regra": row[3],
                    "consenso": row[4],
                    "preco": row[5],
                    "gatilho": row[6],
                }
            )
        return result
    finally:
        conn.close()
