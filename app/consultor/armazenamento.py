import ast
import logging
import re


import json
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

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


def ler_data(texto) -> datetime | None:
    """Lê uma data em ISO 8601 ou RFC 822 (o `pubDate` do RSS), em UTC.

    Nunca levanta exceção: devolve `None` quando não reconhece o texto.
    Data sem fuso é tratada como UTC.
    """
    if texto is None:
        return None
    if isinstance(texto, datetime):
        dt = texto
    else:
        bruto = str(texto).strip()
        if not bruto:
            return None
        try:
            dt = datetime.fromisoformat(bruto.replace("Z", "+00:00"))
        except ValueError:
            try:
                dt = parsedate_to_datetime(bruto)
            except (TypeError, ValueError, IndexError):
                return None
            if dt is None:
                return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def data_iso(texto) -> str | None:
    """A data de `texto` em ISO 8601 UTC, ou `None` se ilegível."""
    dt = ler_data(texto)
    return dt.isoformat() if dt else None


_NUMERO = re.compile(r"\d[\d.,]*")
_MILHAR_COM_PONTO = re.compile(r"^\d{1,3}(\.\d{3})+$")


def ler_preco_alvo(texto) -> float | None:
    """Lê o preço-alvo como o Gemini escreve (`"R$ 1.234,50"`, `"82.5"`).

    Devolve `None` quando não há número; nunca levanta exceção.
    """
    if texto is None or isinstance(texto, bool):
        return None
    if isinstance(texto, (int, float)):
        return float(texto) if texto > 0 else None
    m = _NUMERO.search(str(texto))
    if not m:
        return None
    numero = m.group(0).rstrip(".,")
    if "," in numero:
        numero = numero.replace(".", "").replace(",", ".")
    elif _MILHAR_COM_PONTO.match(numero):
        numero = numero.replace(".", "")
    try:
        valor = float(numero)
    except ValueError:
        return None
    return valor if valor > 0 else None


def migrar_datas_para_iso(conn, backend: str | None) -> int:
    """Reescreve em ISO 8601 UTC as datas gravadas no formato do RSS (spec 158).

    Idempotente: só lê as linhas que ainda não começam por `AAAA-MM-DD`.
    Uma opinião que, convertida, repete outra já gravada é apagada.
    """
    backend = backend or "sqlite"
    nao_iso = "NOT LIKE '____-__-__%'"
    atualizados = 0
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT guid, data_publicacao FROM consultor_fila_materias WHERE data_publicacao {nao_iso}"
        )
        for guid, bruto in cursor.fetchall():
            novo = data_iso(bruto)
            if novo:
                cursor.execute(
                    sql_para(
                        backend,
                        "UPDATE consultor_fila_materias SET data_publicacao = ? WHERE guid = ?",
                    ),
                    (novo, guid),
                )
                atualizados += 1

        cursor.execute(
            f"SELECT id, ticker, casa, recomendacao, data_materia FROM consultor_opinioes WHERE data_materia {nao_iso}"
        )
        for row_id, ticker, casa, recomendacao, bruto in cursor.fetchall():
            novo = data_iso(bruto)
            if not novo:
                continue
            cursor.execute(
                sql_para(
                    backend,
                    "SELECT id FROM consultor_opinioes WHERE ticker = ? AND casa = ? AND recomendacao = ? AND data_materia = ?",
                ),
                (ticker, casa, recomendacao, novo),
            )
            if cursor.fetchone():
                cursor.execute(
                    sql_para(backend, "DELETE FROM consultor_opinioes WHERE id = ?"),
                    (row_id,),
                )
            else:
                cursor.execute(
                    sql_para(
                        backend,
                        "UPDATE consultor_opinioes SET data_materia = ? WHERE id = ?",
                    ),
                    (novo, row_id),
                )
            atualizados += 1
        conn.commit()
    except Exception as e:
        logging.warning(f"Erro ao migrar datas do consultor para ISO: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
    return atualizados


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
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS consultor_telegram_cursor (
                        canal TEXT PRIMARY KEY,
                        ultimo_id INTEGER NOT NULL,
                        atualizado_em TEXT NOT NULL
                    );
                """)
            conn.commit()
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
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS consultor_telegram_cursor (
                    canal TEXT PRIMARY KEY,
                    ultimo_id INTEGER NOT NULL,
                    atualizado_em TEXT NOT NULL
                );
            """)
            conn.commit()

        criar_tabelas_consenso_yahoo(conn)
        migrar_datas_para_iso(conn, backend)
        migrar_consenso_para_json(conn, backend)
    except Exception as e:
        logging.warning(f"Erro ao inicializar banco do consultor: {e}")
    finally:
        conn.close()


# --------------------------------------------------------------------------
# Consenso de analistas do Yahoo Finance (spec 159)
# --------------------------------------------------------------------------

# O SQL vale nos dois backends: sem SERIAL nem AUTOINCREMENT.
SQL_CONSENSO_YAHOO = """
    CREATE TABLE IF NOT EXISTS consultor_consenso_yahoo (
        ticker TEXT NOT NULL,
        data TEXT NOT NULL,
        recomendacao_media REAL NOT NULL,
        analistas INTEGER NOT NULL,
        alvo_medio REAL,
        alvo_minimo REAL,
        alvo_maximo REAL,
        coletado_em TEXT NOT NULL,
        PRIMARY KEY (ticker, data)
    )
"""
SQL_CONSENSO_YAHOO_STATUS = """
    CREATE TABLE IF NOT EXISTS consultor_consenso_yahoo_status (
        status TEXT NOT NULL,
        motivo TEXT,
        desde TEXT NOT NULL,
        ultima_tentativa TEXT
    )
"""


def criar_tabelas_consenso_yahoo(conn) -> None:
    cur = conn.cursor()
    cur.execute(SQL_CONSENSO_YAHOO)
    cur.execute(SQL_CONSENSO_YAHOO_STATUS)
    conn.commit()


def tem_consenso_yahoo(data: str) -> bool:
    """Há leitura gravada para o pregão `data` (AAAA-MM-DD)?"""
    init_db()
    conn, backend = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            sql_para(
                backend, "SELECT 1 FROM consultor_consenso_yahoo WHERE data = ? LIMIT 1"
            ),
            (data,),
        )
        return cur.fetchone() is not None
    finally:
        conn.close()


def save_consenso_yahoo(linhas: list[dict], data: str, coletado_em: str) -> int:
    """Grava as leituras do pregão `data`. Devolve quantas linhas gravou."""
    if not linhas:
        return 0
    init_db()
    conn, backend = get_connection()
    try:
        cur = conn.cursor()
        for ln in linhas:
            valores = (
                ln["ticker"],
                data,
                ln["recomendacao_media"],
                ln["analistas"],
                ln.get("alvo_medio"),
                ln.get("alvo_minimo"),
                ln.get("alvo_maximo"),
                coletado_em,
            )
            if backend == "postgres":
                cur.execute(
                    "INSERT INTO consultor_consenso_yahoo (ticker, data, recomendacao_media, "
                    "analistas, alvo_medio, alvo_minimo, alvo_maximo, coletado_em) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (ticker, data) DO NOTHING",
                    valores,
                )
            else:
                cur.execute(
                    "INSERT OR IGNORE INTO consultor_consenso_yahoo (ticker, data, "
                    "recomendacao_media, analistas, alvo_medio, alvo_minimo, alvo_maximo, "
                    "coletado_em) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    valores,
                )
        conn.commit()
        return len(linhas)
    finally:
        conn.close()


def get_consenso_yahoo(datas: list[str]) -> dict[str, dict]:
    """Leitura mais recente de cada ativo entre as `datas` dadas."""
    if not datas:
        return {}
    init_db()
    conn, backend = get_connection()
    try:
        cur = conn.cursor()
        marcas = ",".join("?" for _ in datas)
        cur.execute(
            sql_para(
                backend,
                "SELECT ticker, data, recomendacao_media, analistas, alvo_medio, "
                "alvo_minimo, alvo_maximo, coletado_em FROM consultor_consenso_yahoo "
                f"WHERE data IN ({marcas}) ORDER BY data ASC",
            ),
            list(datas),
        )
        leituras: dict[str, dict] = {}
        for r in cur.fetchall():
            leituras[r[0]] = {
                "data": r[1],
                "recomendacao_media": float(r[2]),
                "analistas": int(r[3]),
                "alvo_medio": None if r[4] is None else float(r[4]),
                "alvo_minimo": None if r[5] is None else float(r[5]),
                "alvo_maximo": None if r[6] is None else float(r[6]),
                "coletado_em": r[7],
            }
        return leituras
    finally:
        conn.close()


def resumo_consenso_yahoo() -> dict:
    """Última leitura (data, ativos, coletado_em) e o status da fonte."""
    init_db()
    conn, backend = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT data, COUNT(*), MAX(coletado_em) FROM consultor_consenso_yahoo "
            "GROUP BY data ORDER BY data DESC LIMIT 1"
        )
        r = cur.fetchone()
        ultima = {"data": r[0], "ativos": int(r[1]), "coletado_em": r[2]} if r else None
    finally:
        conn.close()
    return {"ultima": ultima, "status": get_consenso_yahoo_status()}


def max_coletado_em_consenso_yahoo() -> str:
    init_db()
    conn, backend = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT MAX(coletado_em) FROM consultor_consenso_yahoo")
        r = cur.fetchone()
        return str(r[0]) if r and r[0] else ""
    finally:
        conn.close()


def get_consenso_yahoo_status() -> dict | None:
    init_db()
    conn, backend = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT status, motivo, desde, ultima_tentativa "
            "FROM consultor_consenso_yahoo_status LIMIT 1"
        )
        r = cur.fetchone()
        if not r:
            return None
        return {
            "status": r[0],
            "motivo": r[1] or "",
            "desde": r[2],
            "ultima_tentativa": r[3] or "",
        }
    finally:
        conn.close()


def set_consenso_yahoo_status(
    status: str, motivo: str, agora: datetime, desde: str | None = None
) -> None:
    """Uma linha só. `desde` preserva o início de um bloqueio que continua."""
    init_db()
    conn, backend = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM consultor_consenso_yahoo_status")
        cur.execute(
            sql_para(
                backend,
                "INSERT INTO consultor_consenso_yahoo_status "
                "(status, motivo, desde, ultima_tentativa) VALUES (?, ?, ?, ?)",
            ),
            (status, motivo, desde or agora.isoformat(), agora.isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def get_telegram_cursor(canal: str) -> int | None:
    """Último ID lido de um canal do Telegram (spec 157), ou None se nunca lido."""
    init_db()
    conn, backend = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            sql_para(
                backend,
                "SELECT ultimo_id FROM consultor_telegram_cursor WHERE canal = ?",
            ),
            (canal,),
        )
        row = cur.fetchone()
        return int(row[0]) if row else None
    finally:
        conn.close()


def set_telegram_cursor(canal: str, ultimo_id: int) -> None:
    """Grava o cursor do canal; sem mensagem nova, só regrava `atualizado_em`."""
    init_db()
    agora = datetime.now(timezone.utc).isoformat()
    conn, backend = get_connection()
    try:
        cur = conn.cursor()
        if backend == "postgres":
            cur.execute(
                "INSERT INTO consultor_telegram_cursor (canal, ultimo_id, atualizado_em) "
                "VALUES (%s, %s, %s) ON CONFLICT (canal) DO UPDATE SET "
                "ultimo_id = EXCLUDED.ultimo_id, atualizado_em = EXCLUDED.atualizado_em",
                (canal, ultimo_id, agora),
            )
        else:
            cur.execute(
                "INSERT OR REPLACE INTO consultor_telegram_cursor (canal, ultimo_id, atualizado_em) "
                "VALUES (?, ?, ?)",
                (canal, ultimo_id, agora),
            )
        conn.commit()
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
    init_db()
    conn, backend = get_connection()
    agora = datetime.now(timezone.utc).isoformat()
    tickers_json = json.dumps(tickers_citados)
    data_convertida = data_iso(data_publicacao)
    if data_convertida is None:
        logging.warning(
            f"Data de publicação ilegível na matéria {guid}: {data_publicacao!r}; usando a hora da coleta"
        )
        data_convertida = agora
    data_publicacao = data_convertida

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


def get_opinioes_historicas(data_referencia: str, dias: int = 30) -> list[dict]:
    init_db()
    conn, backend = get_connection()
    try:
        limite_data_obj = datetime.strptime(data_referencia, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        ) - timedelta(days=dias)
        limite_data = limite_data_obj.isoformat()

        limite_data_fim = f"{data_referencia}T23:59:59"

        cursor = conn.cursor()
        cursor.execute(
            sql_para(
                backend,
                "SELECT id, guid, ticker, casa, recomendacao, preco_alvo, resumo, trecho, data_materia, link, extraida_em "
                "FROM consultor_opinioes WHERE extraida_em >= ? AND extraida_em <= ? ORDER BY extraida_em DESC",
            ),
            (limite_data, limite_data_fim),
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


def ler_consenso(bruto: str) -> dict | str:
    if not bruto:
        return {}

    # 1. Tentar JSON
    try:
        resultado = json.loads(bruto)
        return resultado
    except Exception:
        pass

    # 2. Tentar formato antigo (ast.literal_eval)
    try:
        resultado = ast.literal_eval(bruto)
        if isinstance(resultado, dict):
            return resultado
    except Exception:
        pass

    # 3. Fallback: string original com um aviso
    logging.warning(
        f"Consenso lido em formato texto, não é JSON nem dict Python: {bruto!r}"
    )
    return bruto


def migrar_consenso_para_json(conn=None, backend: str | None = None) -> int:
    """Migra registros legados de consenso gravados em repr de dict para JSON (Spec 132c).

    Idempotente: registros já convertidos para JSON ou que não sejam dicts avaliáveis
    não são alterados. Retorna a quantidade de registros atualizados.
    """
    fechar = False
    if conn is None:
        conn, backend = get_connection()
        fechar = True

    atualizados = 0
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, consenso FROM consultor_recomendacoes WHERE consenso IS NOT NULL AND consenso != ''"
        )
        linhas = cursor.fetchall()
        for row_id, bruto in linhas:
            if not isinstance(bruto, str) or not bruto.strip():
                continue

            # Se já for JSON válido, não precisa migrar
            try:
                json.loads(bruto)
                continue
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

            # Detecta de forma segura formato legado de dict usando ast.literal_eval
            try:
                avaliado = ast.literal_eval(bruto)
                if isinstance(avaliado, dict):
                    novo_json = json.dumps(avaliado, ensure_ascii=False)
                    cursor.execute(
                        sql_para(
                            backend or "sqlite",
                            "UPDATE consultor_recomendacoes SET consenso = ? WHERE id = ?",
                        ),
                        (novo_json, row_id),
                    )
                    atualizados += 1
            except Exception:
                # Não altera se não for dict avaliável
                continue

        conn.commit()
    except Exception as e:
        logging.warning(f"Erro ao executar migração de consenso para JSON: {e}")
    finally:
        if fechar:
            conn.close()

    return atualizados


migrar_consenso_legado = migrar_consenso_para_json
