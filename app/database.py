import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

DB_PATH = "data.db"


@dataclass
class IbovespaData:
    timestamp: datetime
    current_price: float
    previous_close: float
    history_json: str


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


init_db()
