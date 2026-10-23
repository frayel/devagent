import contextvars
import json
import os
import time
from typing import Literal
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

try:
    import psycopg

    PSYCOPG_AVAILABLE = True
except ImportError:
    PSYCOPG_AVAILABLE = False

_backend_cached: Literal["postgres", "sqlite_efemero"] | None = None
_backend_checked = False


def custom_default(obj):
    if isinstance(obj, (datetime, date)):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def serialize_json(payload: dict | list) -> str:
    return json.dumps(payload, default=custom_default)


def _determine_backend() -> Literal["postgres", "sqlite_efemero"]:
    db_url = os.environ.get("DATABASE_URL")
    if (
        db_url
        and (db_url.startswith("postgres://") or db_url.startswith("postgresql://"))
        and PSYCOPG_AVAILABLE
    ):
        for attempt in range(2):
            try:
                with psycopg.connect(db_url, connect_timeout=10):
                    return "postgres"
            except Exception as e:
                logger.warning(
                    f"Failed to connect to Postgres (attempt {attempt + 1}): {e}"
                )
                time.sleep(1)
        return "sqlite_efemero"
    return "sqlite_efemero"


def get_backend_type() -> Literal["postgres", "sqlite_efemero"]:
    global _backend_cached, _backend_checked
    if not _backend_checked:
        _backend_cached = _determine_backend()
        _backend_checked = True
    return _backend_cached or "sqlite_efemero"


def get_connection():
    backend = get_backend_type()
    if backend == "postgres":
        db_url = os.environ.get("DATABASE_URL")
        # Spec says "Postgres inacessível ao subir: até 2 tentativas com 10 s de timeout; depois, SQLite com o mesmo aviso."
        # If it's "postgres", it means it worked at least once at startup.
        # For individual connections, if it fails, maybe we just throw? Or we return postgres connection and if it fails it fails.
        # But wait, the reviewer says "If a database is explicitly configured, connection failures must propagate (fail fast) rather than silently failing over to a completely different database backend."
        if db_url:
            return psycopg.connect(db_url, connect_timeout=10), "postgres"

    from app.database import get_connection as get_sqlite_connection

    return get_sqlite_connection(), "sqlite_efemero"


_db_initialized = False


def init_db():
    global _db_initialized
    if _db_initialized:
        return
    conn, backend = get_connection()
    try:
        if backend == "postgres":
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS snapshots_paineis (
                        painel VARCHAR(255),
                        data_referencia DATE,
                        estado VARCHAR(50),
                        fonte VARCHAR(255),
                        payload JSONB,
                        criado_em TIMESTAMP WITH TIME ZONE,
                        PRIMARY KEY (painel, data_referencia)
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS series_diarias (
                        ticker VARCHAR(50),
                        data_pregao DATE,
                        barras JSONB,
                        criado_em TIMESTAMP WITH TIME ZONE,
                        PRIMARY KEY (ticker, data_pregao)
                    )
                    """
                )
            conn.commit()
        else:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshots_paineis (
                    painel TEXT,
                    data_referencia TEXT,
                    estado TEXT,
                    fonte TEXT,
                    payload TEXT,
                    criado_em TEXT,
                    PRIMARY KEY (painel, data_referencia)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS series_diarias (
                    ticker TEXT,
                    data_pregao TEXT,
                    barras TEXT,
                    criado_em TEXT,
                    PRIMARY KEY (ticker, data_pregao)
                )
                """
            )
            conn.commit()
        _db_initialized = True
    finally:
        conn.close()


_estado_snapshot = contextvars.ContextVar("estado_snapshot", default="ao_vivo")
_data_referencia_snapshot: contextvars.ContextVar[date | None] = contextvars.ContextVar(
    "data_referencia_snapshot", default=None
)


def gravar_snapshot(
    painel: str, data_referencia: date, estado: str, fonte: str, payload: dict
):
    estado_override = _estado_snapshot.get()
    if estado_override and estado_override != "ao_vivo":
        estado = estado_override
    data_override = _data_referencia_snapshot.get()
    if data_override:
        data_referencia = data_override
    init_db()
    conn, backend = get_connection()
    payload_str = serialize_json(payload)
    agora = datetime.now().isoformat()
    try:
        if backend == "postgres":
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO snapshots_paineis (painel, data_referencia, estado, fonte, payload, criado_em)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (painel, data_referencia)
                    DO UPDATE SET estado = EXCLUDED.estado, fonte = EXCLUDED.fonte, payload = EXCLUDED.payload, criado_em = EXCLUDED.criado_em
                    """,
                    (painel, data_referencia, estado, fonte, payload_str, agora),
                )
            conn.commit()
        else:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO snapshots_paineis (painel, data_referencia, estado, fonte, payload, criado_em)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(painel, data_referencia)
                DO UPDATE SET estado = excluded.estado, fonte = excluded.fonte, payload = excluded.payload, criado_em = excluded.criado_em
                """,
                (painel, str(data_referencia), estado, fonte, payload_str, agora),
            )
            conn.commit()
    finally:
        conn.close()


def ler_snapshot(painel: str, data_referencia: date | None = None) -> dict | None:
    init_db()
    conn, backend = get_connection()
    try:
        if backend == "postgres":
            with conn.cursor() as cursor:
                if data_referencia:
                    cursor.execute(
                        "SELECT payload FROM snapshots_paineis WHERE painel = %s AND data_referencia = %s LIMIT 1",
                        (painel, data_referencia),
                    )
                else:
                    cursor.execute(
                        "SELECT payload FROM snapshots_paineis WHERE painel = %s ORDER BY data_referencia DESC LIMIT 1",
                        (painel,),
                    )
                row = cursor.fetchone()
                if row:
                    return row[0] if isinstance(row[0], dict) else json.loads(row[0])
                return None
        else:
            cursor = conn.cursor()
            if data_referencia:
                cursor.execute(
                    "SELECT payload FROM snapshots_paineis WHERE painel = ? AND data_referencia = ? LIMIT 1",
                    (painel, str(data_referencia)),
                )
            else:
                cursor.execute(
                    "SELECT payload FROM snapshots_paineis WHERE painel = ? ORDER BY data_referencia DESC LIMIT 1",
                    (painel,),
                )
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None
    finally:
        conn.close()


def listar_datas(painel: str, limite: int = 10) -> list[str]:
    init_db()
    conn, backend = get_connection()
    try:
        if backend == "postgres":
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT data_referencia FROM snapshots_paineis WHERE painel = %s ORDER BY data_referencia DESC LIMIT %s",
                    (painel, limite),
                )
                rows = cursor.fetchall()
                return [str(row[0]) for row in rows]
        else:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT data_referencia FROM snapshots_paineis WHERE painel = ? ORDER BY data_referencia DESC LIMIT ?",
                (painel, limite),
            )
            rows = cursor.fetchall()
            return [row[0] for row in rows]
    finally:
        conn.close()


def gravar_serie(ticker: str, barras: list[dict]):
    if not barras:
        return
    init_db()
    conn, backend = get_connection()
    agora = datetime.now().isoformat()
    try:
        if backend == "postgres":
            with conn.cursor() as cursor:
                for barra in barras:
                    data_pregao = barra.get("data")
                    barras_str = serialize_json([barra])
                    cursor.execute(
                        """
                        INSERT INTO series_diarias (ticker, data_pregao, barras, criado_em)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (ticker, data_pregao)
                        DO UPDATE SET barras = EXCLUDED.barras, criado_em = EXCLUDED.criado_em
                        """,
                        (ticker, data_pregao, barras_str, agora),
                    )
            conn.commit()
        else:
            cursor = conn.cursor()
            for barra in barras:
                data_pregao = barra.get("data")
                barras_str = serialize_json([barra])
                cursor.execute(
                    """
                    INSERT INTO series_diarias (ticker, data_pregao, barras, criado_em)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(ticker, data_pregao)
                    DO UPDATE SET barras = excluded.barras, criado_em = excluded.criado_em
                    """,
                    (ticker, data_pregao, barras_str, agora),
                )
            conn.commit()
    finally:
        conn.close()


def ler_serie(ticker: str, inicio: date, fim: date) -> list[dict]:
    init_db()
    conn, backend = get_connection()
    try:
        if backend == "postgres":
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT barras FROM series_diarias WHERE ticker = %s AND data_pregao >= %s AND data_pregao <= %s ORDER BY data_pregao ASC",
                    (ticker, inicio, fim),
                )
                rows = cursor.fetchall()
                result: list[dict] = []
                for row in rows:
                    barras = row[0] if isinstance(row[0], list) else json.loads(row[0])
                    result.extend(barras)
                return result
        else:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT barras FROM series_diarias WHERE ticker = ? AND data_pregao >= ? AND data_pregao <= ? ORDER BY data_pregao ASC",
                (ticker, str(inicio), str(fim)),
            )
            rows = cursor.fetchall()
            result = []
            for row in rows:
                barras = json.loads(row[0])
                result.extend(barras)
            return result
    finally:
        conn.close()
