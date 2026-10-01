import sqlite3
from dataclasses import dataclass
import os
from datetime import datetime

DB_PATH = os.environ.get("DATABASE_PATH", "data.db")


@dataclass
class IbovespaData:
    timestamp: datetime
    current_price: float
    previous_close: float
    history_json: str
    fonte: str = "brapi"
    mm21: float | None = None
    mm200: float | None = None


@dataclass
class HighlightsData:
    timestamp: datetime
    highs_json: str
    lows_json: str
    fonte: str = "brapi"
    up_count: int | None = None
    down_count: int | None = None
    total_count: int | None = None


@dataclass
class DolarCorrelationData:
    timestamp: datetime
    positivas_json: str
    negativas_json: str
    fonte: str = "yfinance"


@dataclass
class VolumeAlertsData:
    timestamp: datetime
    alerts_json: str
    fonte: str = "yfinance"


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
            history_json TEXT NOT NULL,
            fonte TEXT NOT NULL DEFAULT 'brapi',
            mm21 REAL,
            mm200 REAL
        )
    """)

    # Migrar a tabela antiga caso exista e não tenha a coluna fonte
    try:
        cursor.execute("SELECT fonte FROM ibovespa_cache LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute(
            "ALTER TABLE ibovespa_cache ADD COLUMN fonte TEXT NOT NULL DEFAULT 'brapi'"
        )

    # Migrar a tabela antiga caso exista e não tenha as colunas mm21 e mm200
    try:
        cursor.execute("SELECT mm21 FROM ibovespa_cache LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE ibovespa_cache ADD COLUMN mm21 REAL")
        cursor.execute("ALTER TABLE ibovespa_cache ADD COLUMN mm200 REAL")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS highlights_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            highs_json TEXT NOT NULL,
            lows_json TEXT NOT NULL,
            fonte TEXT NOT NULL DEFAULT 'brapi',
            up_count INTEGER,
            down_count INTEGER,
            total_count INTEGER
        )
    """)
    # Migrar a tabela antiga caso exista e não tenha a coluna fonte
    try:
        cursor.execute("SELECT fonte FROM highlights_cache LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute(
            "ALTER TABLE highlights_cache ADD COLUMN fonte TEXT NOT NULL DEFAULT 'brapi'"
        )

    # Migrar a tabela antiga caso exista e não tenha colunas de contagem
    try:
        cursor.execute("SELECT up_count FROM highlights_cache LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE highlights_cache ADD COLUMN up_count INTEGER")
        cursor.execute("ALTER TABLE highlights_cache ADD COLUMN down_count INTEGER")
        cursor.execute("ALTER TABLE highlights_cache ADD COLUMN total_count INTEGER")

    # Add index to optimize get_latest_ibovespa_data() which does ORDER BY timestamp DESC LIMIT 1
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ibovespa_cache_timestamp
        ON ibovespa_cache(timestamp DESC)
    """)

    # Add index to optimize get_latest_highlights_data() which does ORDER BY timestamp DESC LIMIT 1
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_highlights_cache_timestamp
        ON highlights_cache(timestamp DESC)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS volume_alerts_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            alerts_json TEXT NOT NULL,
            fonte TEXT NOT NULL DEFAULT 'yfinance'
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_volume_alerts_cache_timestamp
        ON volume_alerts_cache(timestamp DESC)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dolar_correlation_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            positivas_json TEXT NOT NULL,
            negativas_json TEXT NOT NULL,
            fonte TEXT NOT NULL DEFAULT 'yfinance'
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_dolar_correlation_cache_timestamp
        ON dolar_correlation_cache(timestamp DESC)
    """)
    conn.commit()
    conn.close()


def save_ibovespa_data(data: IbovespaData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO ibovespa_cache (timestamp, current_price, previous_close, history_json, fonte, mm21, mm200)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            data.timestamp.isoformat(),
            data.current_price,
            data.previous_close,
            data.history_json,
            data.fonte,
            data.mm21,
            data.mm200,
        ),
    )
    conn.commit()
    conn.close()


def get_latest_ibovespa_data() -> IbovespaData | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, current_price, previous_close, history_json, fonte, mm21, mm200
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
            fonte=row["fonte"],
            mm21=row["mm21"],
            mm200=row["mm200"],
        )
    return None


def save_highlights_data(data: HighlightsData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO highlights_cache (timestamp, highs_json, lows_json, fonte, up_count, down_count, total_count)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            data.timestamp.isoformat(),
            data.highs_json,
            data.lows_json,
            data.fonte,
            data.up_count,
            data.down_count,
            data.total_count,
        ),
    )
    conn.commit()
    conn.close()


def get_latest_highlights_data() -> HighlightsData | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, highs_json, lows_json, fonte, up_count, down_count, total_count
        FROM highlights_cache
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()

    if row:
        return HighlightsData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            highs_json=row["highs_json"],
            lows_json=row["lows_json"],
            fonte=row["fonte"],
            up_count=row["up_count"],
            down_count=row["down_count"],
            total_count=row["total_count"],
        )
    return None


def save_volume_alerts_data(data: VolumeAlertsData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO volume_alerts_cache (timestamp, alerts_json, fonte)
        VALUES (?, ?, ?)
    """,
        (
            data.timestamp.isoformat(),
            data.alerts_json,
            data.fonte,
        ),
    )
    conn.commit()
    conn.close()


def get_latest_volume_alerts_data() -> VolumeAlertsData | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, alerts_json, fonte
        FROM volume_alerts_cache
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()

    if row:
        return VolumeAlertsData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            alerts_json=row["alerts_json"],
            fonte=row["fonte"],
        )
    return None


def save_dolar_correlation_data(data: DolarCorrelationData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO dolar_correlation_cache (timestamp, positivas_json, negativas_json, fonte)
        VALUES (?, ?, ?, ?)
    """,
        (
            data.timestamp.isoformat(),
            data.positivas_json,
            data.negativas_json,
            data.fonte,
        ),
    )
    conn.commit()
    conn.close()


def get_latest_dolar_correlation_data() -> DolarCorrelationData | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, positivas_json, negativas_json, fonte
        FROM dolar_correlation_cache
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()

    if row:
        return DolarCorrelationData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            positivas_json=row["positivas_json"],
            negativas_json=row["negativas_json"],
            fonte=row["fonte"],
        )
    return None


init_db()
