import sqlite3
from dataclasses import dataclass
from datetime import datetime

DB_PATH = "data.db"


@dataclass
class IbovespaData:
    timestamp: datetime
    current_price: float
    previous_close: float
    history_json: str


@dataclass
class AltasBaixasData:
    timestamp: datetime
    top_altas_json: str
    top_baixas_json: str
    source: str


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ibovespa_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            current_price REAL NOT NULL,
            previous_close REAL NOT NULL,
            history_json TEXT NOT NULL
        )
    """)
    # Add index to optimize get_latest_ibovespa_data() which does ORDER BY timestamp DESC LIMIT 1
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ibovespa_cache_timestamp
        ON ibovespa_cache(timestamp DESC)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS altas_baixas_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            top_altas_json TEXT NOT NULL,
            top_baixas_json TEXT NOT NULL,
            source TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_altas_baixas_cache_timestamp
        ON altas_baixas_cache(timestamp DESC)
    """)
    conn.commit()
    conn.close()


def save_ibovespa_data(data: IbovespaData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO ibovespa_cache (timestamp, current_price, previous_close, history_json)
        VALUES (?, ?, ?, ?)
    """,
        (
            data.timestamp.isoformat(),
            data.current_price,
            data.previous_close,
            data.history_json,
        ),
    )
    conn.commit()
    conn.close()


def get_latest_ibovespa_data() -> IbovespaData | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, current_price, previous_close, history_json
        FROM ibovespa_cache
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()

    if row:
        return IbovespaData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            current_price=row["current_price"],
            previous_close=row["previous_close"],
            history_json=row["history_json"],
        )
    return None


def save_altas_baixas_data(data: AltasBaixasData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO altas_baixas_cache (timestamp, top_altas_json, top_baixas_json, source)
        VALUES (?, ?, ?, ?)
    """,
        (
            data.timestamp.isoformat(),
            data.top_altas_json,
            data.top_baixas_json,
            data.source,
        ),
    )
    conn.commit()
    conn.close()


def get_latest_altas_baixas_data() -> AltasBaixasData | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, top_altas_json, top_baixas_json, source
        FROM altas_baixas_cache
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()

    if row:
        return AltasBaixasData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            top_altas_json=row["top_altas_json"],
            top_baixas_json=row["top_baixas_json"],
            source=row["source"],
        )
    return None


init_db()
