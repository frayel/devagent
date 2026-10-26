import contextvars
import json
import os
import time
from typing import Literal
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

PREGOES_NO_SELETOR = 5

try:
    import importlib.util

    PSYCOPG_AVAILABLE = importlib.util.find_spec("psycopg") is not None
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
                import psycopg

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
            import psycopg

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
                    "CREATE INDEX IF NOT EXISTS idx_snapshots_paineis_painel_data_referencia ON snapshots_paineis(painel, data_referencia DESC);"
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
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS simbolos_sem_cotacao (
                        fonte VARCHAR(50),
                        simbolo VARCHAR(50),
                        desde TIMESTAMP WITH TIME ZONE,
                        ultimo_status TIMESTAMP WITH TIME ZONE,
                        tentativas INTEGER,
                        PRIMARY KEY (fonte, simbolo)
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
                "CREATE INDEX IF NOT EXISTS idx_snapshots_paineis_painel_data_referencia ON snapshots_paineis(painel, data_referencia DESC)"
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
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS simbolos_sem_cotacao (
                    fonte TEXT,
                    simbolo TEXT,
                    desde TEXT,
                    ultimo_status TEXT,
                    tentativas INTEGER,
                    PRIMARY KEY (fonte, simbolo)
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
                    "SELECT data_referencia FROM snapshots_paineis WHERE painel = %s AND estado IN ('final', 'incompleto', 'ok') ORDER BY data_referencia DESC LIMIT %s",
                    (painel, limite),
                )
                rows = cursor.fetchall()
                return [str(row[0]) for row in rows]
        else:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT data_referencia FROM snapshots_paineis WHERE painel = ? AND estado IN ('final', 'incompleto', 'ok') ORDER BY data_referencia DESC LIMIT ?",
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


def ler_series(tickers: list[str], inicio: date, fim: date) -> dict[str, list[dict]]:
    init_db()
    conn, backend = get_connection()
    try:
        if backend == "postgres":
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT ticker, barras, criado_em FROM series_diarias WHERE ticker = ANY(%s) AND data_pregao >= %s AND data_pregao <= %s ORDER BY data_pregao ASC",
                    (tickers, inicio, fim),
                )
                rows = cursor.fetchall()
                res_pg: dict[str, list[dict]] = {t: [] for t in tickers}
                for row in rows:
                    t = row[0]
                    barras = row[1] if isinstance(row[1], list) else json.loads(row[1])
                    criado_em = (
                        row[2]
                        if isinstance(row[2], str)
                        else str(row[2])
                        if row[2]
                        else ""
                    )
                    if barras and isinstance(barras, list):
                        for b in barras:
                            if "criado_em" not in b:
                                b["criado_em"] = criado_em
                    if t in res_pg:
                        res_pg[t].extend(barras)
                return res_pg
        else:
            cursor = conn.cursor()
            placeholders = ",".join(["?"] * len(tickers))
            query = f"SELECT ticker, barras, criado_em FROM series_diarias WHERE ticker IN ({placeholders}) AND data_pregao >= ? AND data_pregao <= ? ORDER BY data_pregao ASC"
            params = tuple(tickers) + (str(inicio), str(fim))
            cursor.execute(query, params)
            rows = cursor.fetchall()
            res_sqlite: dict[str, list[dict]] = {t: [] for t in tickers}
            for row in rows:
                t = row[0]
                barras = json.loads(row[1])
                criado_em = row[2]
                if barras and isinstance(barras, list):
                    for b in barras:
                        if "criado_em" not in b:
                            b["criado_em"] = criado_em
                if t in res_sqlite:
                    res_sqlite[t].extend(barras)
            return res_sqlite
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


def diagnostico() -> dict:
    import time
    import os
    from app.database import DB_PATH

    tipo = get_backend_type()

    info: dict = {
        "tipo": "Postgres" if tipo == "postgres" else "SQLite",
        "database_url": bool(os.environ.get("DATABASE_URL", "").strip()),
    }
    inicio = time.perf_counter()
    try:
        conn, backend = get_connection()
        try:
            if backend == "postgres":
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"
                    )
                    tabelas = cursor.fetchone()[0]
                    cursor.execute("SELECT pg_database_size(current_database())")
                    tamanho = cursor.fetchone()[0]
                    info["tamanho"] = (
                        f"{tamanho / 1_048_576:.1f} MB".replace(".", ",")
                        if tamanho >= 1_048_576
                        else f"{tamanho // 1024} KB"
                    )
            else:
                cursor = conn.cursor()
                tabelas = cursor.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'"
                ).fetchone()[0]
                try:
                    tamanho = os.path.getsize(DB_PATH)
                    info["tamanho"] = (
                        f"{tamanho / 1_048_576:.1f} MB".replace(".", ",")
                        if tamanho >= 1_048_576
                        else f"{tamanho // 1024} KB"
                    )
                except OSError:
                    info["tamanho"] = "?"
        finally:
            conn.close()
    except Exception as e:
        info["erro"] = f"{type(e).__name__}: {e}"[:200]
        return info
    info["latencia_ms"] = round((time.perf_counter() - inicio) * 1000)
    info["tabelas"] = tabelas
    return info


def remover_snapshots_antigos(dias: int = 30):
    init_db()
    conn, backend = get_connection()
    try:
        if backend == "postgres":
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM snapshots_paineis WHERE data_referencia NOT IN (SELECT data_referencia FROM (SELECT DISTINCT data_referencia FROM snapshots_paineis ORDER BY data_referencia DESC LIMIT %s) as t)",
                    (dias,),
                )
            conn.commit()
        else:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM snapshots_paineis WHERE data_referencia NOT IN (SELECT DISTINCT data_referencia FROM snapshots_paineis ORDER BY data_referencia DESC LIMIT ?)",
                (dias,),
            )
            conn.commit()
    finally:
        conn.close()


def registrar_falha_simbolo(fonte: str, simbolo: str, sucesso: bool = False) -> None:
    init_db()
    conn, backend = get_connection()
    try:
        from datetime import datetime, timezone

        agora = datetime.now(timezone.utc)
        agora_str = agora.isoformat()

        if backend == "postgres":
            with conn.cursor() as cursor:
                if sucesso:
                    cursor.execute(
                        "DELETE FROM simbolos_sem_cotacao WHERE fonte = %s AND simbolo = %s",
                        (fonte, simbolo),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO simbolos_sem_cotacao (fonte, simbolo, desde, ultimo_status, tentativas)
                        VALUES (%s, %s, %s, %s, 1)
                        ON CONFLICT (fonte, simbolo)
                        DO UPDATE SET
                            ultimo_status = EXCLUDED.ultimo_status,
                            tentativas = simbolos_sem_cotacao.tentativas + 1
                        """,
                        (fonte, simbolo, agora_str, agora_str),
                    )
            conn.commit()
        else:
            cursor = conn.cursor()
            if sucesso:
                cursor.execute(
                    "DELETE FROM simbolos_sem_cotacao WHERE fonte = ? AND simbolo = ?",
                    (fonte, simbolo),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO simbolos_sem_cotacao (fonte, simbolo, desde, ultimo_status, tentativas)
                    VALUES (?, ?, ?, ?, 1)
                    ON CONFLICT(fonte, simbolo)
                    DO UPDATE SET
                        ultimo_status = excluded.ultimo_status,
                        tentativas = simbolos_sem_cotacao.tentativas + 1
                    """,
                    (fonte, simbolo, agora_str, agora_str),
                )
            conn.commit()
    finally:
        conn.close()


def is_simbolo_suspenso(fonte: str, simbolo: str) -> bool:
    init_db()
    conn, backend = get_connection()
    try:
        from datetime import datetime, timezone, timedelta

        if backend == "postgres":
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT ultimo_status, tentativas FROM simbolos_sem_cotacao WHERE fonte = %s AND simbolo = %s",
                    (fonte, simbolo),
                )
                row = cursor.fetchone()
                if not row:
                    return False
                ultimo_status, tentativas = row

                if isinstance(ultimo_status, str):
                    ultimo_status = datetime.fromisoformat(ultimo_status)

                if tentativas >= 3:
                    agora = datetime.now(timezone.utc)
                    if (agora - ultimo_status) < timedelta(hours=24):
                        return True
                return False
        else:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT ultimo_status, tentativas FROM simbolos_sem_cotacao WHERE fonte = ? AND simbolo = ?",
                (fonte, simbolo),
            )
            row = cursor.fetchone()
            if not row:
                return False
            ultimo_status_str, tentativas = row

            ultimo_status = datetime.fromisoformat(ultimo_status_str)
            if tentativas >= 3:
                agora = datetime.now(timezone.utc)
                if (agora - ultimo_status) < timedelta(hours=24):
                    return True
            return False
    finally:
        conn.close()


def get_simbolos_suspensos() -> list[dict]:
    init_db()
    conn, backend = get_connection()
    try:
        if backend == "postgres":
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT fonte, simbolo, desde, ultimo_status, tentativas FROM simbolos_sem_cotacao WHERE tentativas >= 3"
                )
                rows = cursor.fetchall()
                return [
                    {
                        "fonte": row[0],
                        "simbolo": row[1],
                        "desde": str(row[2]),
                        "ultimo_status": str(row[3]),
                        "tentativas": row[4],
                    }
                    for row in rows
                ]
        else:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT fonte, simbolo, desde, ultimo_status, tentativas FROM simbolos_sem_cotacao WHERE tentativas >= 3"
            )
            rows = cursor.fetchall()
            return [
                {
                    "fonte": row[0],
                    "simbolo": row[1],
                    "desde": row[2],
                    "ultimo_status": row[3],
                    "tentativas": row[4],
                }
                for row in rows
            ]
    finally:
        conn.close()
