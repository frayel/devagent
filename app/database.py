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
class FatorMolaData:
    timestamp: datetime
    top3_json: str
    fonte: str = "yfinance"


@dataclass
class EscudoQuedasData:
    timestamp: datetime
    top3_json: str
    fonte: str = "yfinance"


@dataclass
class ForcaRelativaData:
    timestamp: datetime
    maior_json: str
    menor_json: str
    fonte: str = "yfinance"


@dataclass
class AtrasadasRallyData:
    timestamp: datetime
    rally_valido: bool
    top3_json: str
    fonte: str


@dataclass
class CoesaoData:
    timestamp: datetime
    concordantes: int
    total: int
    fonte: str = "yfinance"


@dataclass
class VolumeAlertsData:
    timestamp: datetime
    alerts_json: str
    fonte: str = "yfinance"


@dataclass
class ConcentracaoData:
    timestamp: datetime
    resumo_json: str
    top3_json: str
    fonte: str = "yfinance"


@dataclass
class VariacaoSubitaData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "yfinance"


@dataclass
class ConcentracaoSetorialData:
    timestamp: datetime
    setor_destaque: str
    variacao_media: float
    fonte: str = "brapi"
    setor_lider_volume: str = ""
    volume_lider: float = 0.0


@dataclass
class ApetiteRiscoData:
    timestamp: datetime
    estado: str
    diferenca: float
    fonte: str = "yfinance"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@dataclass
class ScannerCapitulacaoData:
    timestamp: datetime
    alertas_json: str
    fonte: str


@dataclass
class MareData:
    """Maré do mercado (spec 027). Componente ausente fica None."""

    timestamp: datetime
    valor: int
    fluxo: float | None
    calma: float | None
    volume: float | None
    historico_json: str
    fonte: str


@dataclass
class RotacaoCapitalData:
    timestamp: datetime
    estado: str
    var_bancos: float
    var_commodities: float
    fonte: str


@dataclass
class VolatilidadeSilenciosaData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "yfinance"


def save_volatilidade_silenciosa_data(data: VolatilidadeSilenciosaData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO volatilidade_silenciosa_cache (timestamp, alertas_json, fonte)
        VALUES (?, ?, ?)
        """,
        (
            data.timestamp.isoformat(),
            data.alertas_json,
            data.fonte,
        ),
    )
    conn.commit()
    conn.close()


def get_latest_volatilidade_silenciosa_data() -> VolatilidadeSilenciosaData | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT timestamp, alertas_json, fonte
            FROM volatilidade_silenciosa_cache
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
    except sqlite3.OperationalError:
        row = None
    finally:
        conn.close()
    if row:
        return VolatilidadeSilenciosaData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            alertas_json=row["alertas_json"],
            fonte=row["fonte"],
        )
    return None


def init_db() -> None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS radar_congestionamento_cache (
            timestamp TEXT,
            alertas_json TEXT,
            fonte TEXT
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_radar_congestionamento_timestamp ON radar_congestionamento_cache (timestamp DESC)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scanner_capitulacao_cache (
            timestamp TEXT,
            alertas_json TEXT,
            fonte TEXT
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_scanner_capitulacao_cache_timestamp ON scanner_capitulacao_cache (timestamp DESC)"
    )
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS volatilidade_silenciosa_cache (
            timestamp TEXT,
            alertas_json TEXT,
            fonte TEXT
        )
        """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_volatilidade_silenciosa_timestamp ON volatilidade_silenciosa_cache (timestamp DESC)
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS armadilha_abertura_cache (
            timestamp TEXT,
            alertas_json TEXT,
            fonte TEXT
        )
        """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_armadilha_abertura_timestamp ON armadilha_abertura_cache (timestamp DESC)
        """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sobrevivencia_semanal_cache (
            timestamp TEXT,
            alertas_json TEXT,
            fonte TEXT
        )
        """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sobrevivencia_semanal_timestamp ON sobrevivencia_semanal_cache (timestamp DESC)
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS compradores_fundo_cache (
            timestamp TEXT,
            alertas_json TEXT,
            fonte TEXT
        )
        """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_compradores_fundo_timestamp ON compradores_fundo_cache (timestamp DESC)
        """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS faca_caindo_cache (
            timestamp TEXT,
            alertas_json TEXT,
            fonte TEXT
        )
        """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_faca_caindo_timestamp ON faca_caindo_cache (timestamp DESC)
        """)
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
        CREATE TABLE IF NOT EXISTS variacao_subita_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            alertas_json TEXT NOT NULL,
            fonte TEXT NOT NULL DEFAULT 'yfinance'
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_variacao_subita_timestamp ON variacao_subita_cache(timestamp DESC)"
    )
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rotacao_capital_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            estado TEXT NOT NULL,
            var_bancos REAL NOT NULL,
            var_commodities REAL NOT NULL,
            fonte TEXT NOT NULL
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_rotacao_capital_timestamp ON rotacao_capital_cache(timestamp DESC)"
    )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS concentracao_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            resumo_json TEXT NOT NULL,
            top3_json TEXT NOT NULL,
            fonte TEXT NOT NULL DEFAULT 'yfinance'
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_concentracao_cache_timestamp
        ON concentracao_cache(timestamp DESC)
    """)
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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fator_mola_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            top3_json TEXT NOT NULL,
            fonte TEXT NOT NULL DEFAULT 'yfinance'
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_fator_mola_cache_timestamp
        ON fator_mola_cache(timestamp DESC)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS escudo_quedas_cache (
            timestamp TEXT PRIMARY KEY,
            top3_json TEXT NOT NULL,
            fonte TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_escudo_quedas_cache_timestamp
        ON escudo_quedas_cache(timestamp DESC)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS forca_relativa_cache (
            timestamp TEXT PRIMARY KEY,
            maior_json TEXT NOT NULL,
            menor_json TEXT NOT NULL,
            fonte TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_forca_relativa_cache_timestamp
        ON forca_relativa_cache(timestamp DESC)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS coesao_cache (
            timestamp TEXT PRIMARY KEY,
            concordantes INTEGER NOT NULL,
            total INTEGER NOT NULL,
            fonte TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_coesao_cache_timestamp
        ON coesao_cache(timestamp DESC)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS atrasadas_rally_cache (
            timestamp TEXT PRIMARY KEY,
            rally_valido INTEGER NOT NULL,
            top3_json TEXT NOT NULL,
            fonte TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_atrasadas_rally_cache_timestamp
        ON atrasadas_rally_cache(timestamp DESC)
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS concentracao_setorial_cache (
            timestamp TEXT PRIMARY KEY,
            setor_destaque TEXT NOT NULL,
            variacao_media REAL NOT NULL,
            fonte TEXT NOT NULL,
            setor_lider_volume TEXT NOT NULL DEFAULT "",
            volume_lider REAL NOT NULL DEFAULT 0.0
        )
    """)
    # Migrar a tabela antiga caso exista e não tenha as colunas de volume
    try:
        cursor.execute(
            "SELECT setor_lider_volume FROM concentracao_setorial_cache LIMIT 1"
        )
    except sqlite3.OperationalError:
        cursor.execute(
            "ALTER TABLE concentracao_setorial_cache ADD COLUMN setor_lider_volume TEXT NOT NULL DEFAULT ''"
        )
        cursor.execute(
            "ALTER TABLE concentracao_setorial_cache ADD COLUMN volume_lider REAL NOT NULL DEFAULT 0.0"
        )
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_concentracao_setorial_cache_timestamp
        ON concentracao_setorial_cache(timestamp DESC)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mare_cache (
            timestamp TEXT PRIMARY KEY,
            valor INTEGER NOT NULL,
            fluxo REAL,
            calma REAL,
            volume REAL,
            historico_json TEXT NOT NULL,
            fonte TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_mare_cache_timestamp
        ON mare_cache(timestamp DESC)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS apetite_risco_cache (
            timestamp TEXT PRIMARY KEY,
            estado TEXT NOT NULL,
            diferenca REAL NOT NULL,
            fonte TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS anomalia_peso_cache (
            timestamp TEXT PRIMARY KEY,
            alertas_json TEXT NOT NULL,
            fonte TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS radar_inflexao_cache (
            timestamp TEXT PRIMARY KEY,
            alertas_json TEXT NOT NULL,
            fonte TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS radar_short_squeeze_cache (
            timestamp TEXT PRIMARY KEY,
            alertas_json TEXT NOT NULL,
            fonte TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_apetite_risco_cache_timestamp
        ON apetite_risco_cache(timestamp DESC)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_anomalia_peso_cache_timestamp
        ON anomalia_peso_cache(timestamp DESC)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_radar_inflexao_cache_timestamp
        ON radar_inflexao_cache(timestamp DESC)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_radar_short_squeeze_cache_timestamp
        ON radar_short_squeeze_cache(timestamp DESC)
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


def save_fator_mola_data(data: FatorMolaData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO fator_mola_cache (timestamp, top3_json, fonte)
        VALUES (?, ?, ?)
    """,
        (
            data.timestamp.isoformat(),
            data.top3_json,
            data.fonte,
        ),
    )
    conn.commit()
    conn.close()


def get_latest_fator_mola_data() -> FatorMolaData | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, top3_json, fonte
        FROM fator_mola_cache
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()

    if row:
        return FatorMolaData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            top3_json=row["top3_json"],
            fonte=row["fonte"],
        )
    return None


init_db()


def save_scanner_capitulacao_data(data: ScannerCapitulacaoData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO scanner_capitulacao_cache (timestamp, alertas_json, fonte) VALUES (?, ?, ?)",
        (data.timestamp.isoformat(), data.alertas_json, data.fonte),
    )
    conn.commit()


def get_latest_scanner_capitulacao_data() -> ScannerCapitulacaoData | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT * FROM scanner_capitulacao_cache ORDER BY timestamp DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            return ScannerCapitulacaoData(
                timestamp=datetime.fromisoformat(row["timestamp"]),
                alertas_json=row["alertas_json"],
                fonte=row["fonte"],
            )
    except sqlite3.OperationalError:
        return None
    return None


def save_forca_relativa_data(data: ForcaRelativaData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO forca_relativa_cache (timestamp, maior_json, menor_json, fonte)
        VALUES (?, ?, ?, ?)
        """,
        (data.timestamp.isoformat(), data.maior_json, data.menor_json, data.fonte),
    )
    conn.commit()


def get_latest_forca_relativa_data() -> ForcaRelativaData | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, maior_json, menor_json, fonte
        FROM forca_relativa_cache
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    if row:
        return ForcaRelativaData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            maior_json=row["maior_json"],
            menor_json=row["menor_json"],
            fonte=row["fonte"],
        )
    return None


def save_escudo_quedas_data(data: EscudoQuedasData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO escudo_quedas_cache (timestamp, top3_json, fonte)
        VALUES (?, ?, ?)
        """,
        (data.timestamp.isoformat(), data.top3_json, data.fonte),
    )
    conn.commit()


def get_latest_escudo_quedas_data() -> EscudoQuedasData | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, top3_json, fonte
        FROM escudo_quedas_cache
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    if row:
        return EscudoQuedasData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            top3_json=row["top3_json"],
            fonte=row["fonte"],
        )
    return None


def save_coesao_data(data: CoesaoData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO coesao_cache (timestamp, concordantes, total, fonte)
            VALUES (?, ?, ?, ?)
            """,
            (data.timestamp.isoformat(), data.concordantes, data.total, data.fonte),
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass
    conn.close()


def get_latest_coesao_data() -> CoesaoData | None:
    conn = get_connection()
    cursor = conn.cursor()
    row = None
    try:
        cursor.execute("""
            SELECT timestamp, concordantes, total, fonte
            FROM coesao_cache
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
    except sqlite3.OperationalError:
        pass
    conn.close()
    if row:
        return CoesaoData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            concordantes=row["concordantes"],
            total=row["total"],
            fonte=row["fonte"],
        )
    return None


def save_atrasadas_rally_data(data: AtrasadasRallyData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO atrasadas_rally_cache (timestamp, rally_valido, top3_json, fonte)
        VALUES (?, ?, ?, ?)
        """,
        (
            data.timestamp.isoformat(),
            1 if data.rally_valido else 0,
            data.top3_json,
            data.fonte,
        ),
    )
    conn.commit()
    conn.close()


def get_latest_atrasadas_rally_data() -> AtrasadasRallyData | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT timestamp, rally_valido, top3_json, fonte
            FROM atrasadas_rally_cache
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
    except sqlite3.OperationalError:
        row = None
    conn.close()
    if row:
        return AtrasadasRallyData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            rally_valido=bool(row["rally_valido"]),
            top3_json=row["top3_json"],
            fonte=row["fonte"],
        )
    return None


def save_concentracao_data(data: ConcentracaoData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO concentracao_cache (timestamp, resumo_json, top3_json, fonte)
        VALUES (?, ?, ?, ?)
        """,
        (
            data.timestamp.isoformat(),
            data.resumo_json,
            data.top3_json,
            data.fonte,
        ),
    )
    conn.commit()
    conn.close()


def get_latest_concentracao_data() -> ConcentracaoData | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT timestamp, resumo_json, top3_json, fonte
        FROM concentracao_cache
        ORDER BY timestamp DESC LIMIT 1
        """
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return ConcentracaoData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            resumo_json=row["resumo_json"],
            top3_json=row["top3_json"],
            fonte=row["fonte"],
        )
    return None


def save_variacao_subita_data(data: VariacaoSubitaData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO variacao_subita_cache (timestamp, alertas_json, fonte)
        VALUES (?, ?, ?)
        """,
        (
            data.timestamp.isoformat(),
            data.alertas_json,
            data.fonte,
        ),
    )
    conn.commit()
    conn.close()


def get_latest_variacao_subita_data() -> VariacaoSubitaData | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, alertas_json, fonte
        FROM variacao_subita_cache
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()

    if row:
        return VariacaoSubitaData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            alertas_json=row["alertas_json"],
            fonte=row["fonte"],
        )
    return None


def save_concentracao_setorial_data(data: ConcentracaoSetorialData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO concentracao_setorial_cache (timestamp, setor_destaque, variacao_media, fonte, setor_lider_volume, volume_lider)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            data.timestamp.isoformat(),
            data.setor_destaque,
            data.variacao_media,
            data.fonte,
            data.setor_lider_volume,
            data.volume_lider,
        ),
    )
    conn.commit()
    conn.close()


def get_latest_concentracao_setorial_data() -> ConcentracaoSetorialData | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT * FROM concentracao_setorial_cache
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
    except sqlite3.OperationalError:
        row = None
    finally:
        conn.close()
    if row:
        return ConcentracaoSetorialData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            setor_destaque=row["setor_destaque"],
            variacao_media=float(row["variacao_media"]),
            fonte=row["fonte"],
            setor_lider_volume=row["setor_lider_volume"]
            if "setor_lider_volume" in row.keys()
            else "",
            volume_lider=float(row["volume_lider"])
            if "volume_lider" in row.keys() and row["volume_lider"] is not None
            else 0.0,
        )
    return None


def save_apetite_risco_data(data: ApetiteRiscoData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO apetite_risco_cache (timestamp, estado, diferenca, fonte)
        VALUES (?, ?, ?, ?)
        """,
        (
            data.timestamp.isoformat(),
            data.estado,
            data.diferenca,
            data.fonte,
        ),
    )
    conn.commit()
    conn.close()


def get_latest_apetite_risco_data() -> ApetiteRiscoData | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT timestamp, estado, diferenca, fonte
            FROM apetite_risco_cache
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
    except sqlite3.OperationalError:
        row = None
    conn.close()
    if row:
        return ApetiteRiscoData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            estado=row["estado"],
            diferenca=row["diferenca"],
            fonte=row["fonte"],
        )
    return None


def save_rotacao_capital_data(data: RotacaoCapitalData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO rotacao_capital_cache (timestamp, estado, var_bancos, var_commodities, fonte)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            data.timestamp.isoformat(),
            data.estado,
            data.var_bancos,
            data.var_commodities,
            data.fonte,
        ),
    )
    conn.commit()
    conn.close()


def get_latest_rotacao_capital_data() -> RotacaoCapitalData | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, estado, var_bancos, var_commodities, fonte
        FROM rotacao_capital_cache
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()

    if row:
        return RotacaoCapitalData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            estado=row["estado"],
            var_bancos=row["var_bancos"],
            var_commodities=row["var_commodities"],
            fonte=row["fonte"],
        )
    return None


@dataclass
class FacaCaindoData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "yfinance"


def save_faca_caindo_data(data: FacaCaindoData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO faca_caindo_cache (timestamp, alertas_json, fonte)
        VALUES (?, ?, ?)
        """,
        (
            data.timestamp.isoformat(),
            data.alertas_json,
            data.fonte,
        ),
    )
    conn.commit()
    conn.close()


def get_latest_faca_caindo_data() -> FacaCaindoData | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT timestamp, alertas_json, fonte
            FROM faca_caindo_cache
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
    except sqlite3.OperationalError:
        row = None
    conn.close()
    if row:
        return FacaCaindoData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            alertas_json=row["alertas_json"],
            fonte=row["fonte"],
        )
    return None


@dataclass
class CompradoresFundoData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "yfinance"


def save_compradores_fundo_data(data: CompradoresFundoData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO compradores_fundo_cache (timestamp, alertas_json, fonte)
        VALUES (?, ?, ?)
        """,
        (
            data.timestamp.isoformat(),
            data.alertas_json,
            data.fonte,
        ),
    )
    conn.commit()
    conn.close()


def get_latest_compradores_fundo_data() -> CompradoresFundoData | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT timestamp, alertas_json, fonte
            FROM compradores_fundo_cache
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
    except sqlite3.OperationalError:
        row = None
    conn.close()
    if row:
        return CompradoresFundoData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            alertas_json=row["alertas_json"],
            fonte=row["fonte"],
        )
    return None


@dataclass
class ArmadilhaAberturaData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "yfinance"


def save_armadilha_abertura_data(data: ArmadilhaAberturaData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO armadilha_abertura_cache (timestamp, alertas_json, fonte)
        VALUES (?, ?, ?)
        """,
        (
            data.timestamp.isoformat(),
            data.alertas_json,
            data.fonte,
        ),
    )
    conn.commit()
    conn.close()


def get_latest_armadilha_abertura_data() -> ArmadilhaAberturaData | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT timestamp, alertas_json, fonte
            FROM armadilha_abertura_cache
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()

    if row:
        return ArmadilhaAberturaData(
            timestamp=datetime.fromisoformat(row[0]),
            alertas_json=row[1],
            fonte=row[2],
        )
    return None


@dataclass
class SobrevivenciaSemanalData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "yfinance"


def save_sobrevivencia_semanal_data(data: SobrevivenciaSemanalData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO sobrevivencia_semanal_cache (timestamp, alertas_json, fonte)
        VALUES (?, ?, ?)
        """,
        (
            data.timestamp.isoformat(),
            data.alertas_json,
            data.fonte,
        ),
    )
    conn.commit()
    conn.close()


def get_latest_sobrevivencia_semanal_data() -> SobrevivenciaSemanalData | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT timestamp, alertas_json, fonte
            FROM sobrevivencia_semanal_cache
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()

    if row:
        return SobrevivenciaSemanalData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            alertas_json=row["alertas_json"],
            fonte=row["fonte"],
        )
    return None


def save_mare_data(data: MareData) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO mare_cache
                (timestamp, valor, fluxo, calma, volume, historico_json, fonte)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.timestamp.isoformat(),
                data.valor,
                data.fluxo,
                data.calma,
                data.volume,
                data.historico_json,
                data.fonte,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_latest_mare_data() -> MareData | None:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT timestamp, valor, fluxo, calma, volume, historico_json, fonte
            FROM mare_cache
            ORDER BY timestamp DESC
            LIMIT 1
            """
        ).fetchone()
    except sqlite3.OperationalError:
        row = None
    finally:
        conn.close()
    if not row:
        return None
    return MareData(
        timestamp=datetime.fromisoformat(row["timestamp"]),
        valor=int(row["valor"]),
        fluxo=row["fluxo"],
        calma=row["calma"],
        volume=row["volume"],
        historico_json=row["historico_json"],
        fonte=row["fonte"],
    )


@dataclass
class AnomaliaPesoData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "yfinance"


def save_anomalia_peso_data(data: AnomaliaPesoData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO anomalia_peso_cache (timestamp, alertas_json, fonte) VALUES (?, ?, ?)""",
        (data.timestamp.isoformat(), data.alertas_json, data.fonte),
    )
    conn.commit()
    conn.close()


def get_latest_anomalia_peso_data() -> AnomaliaPesoData | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """SELECT timestamp, alertas_json, fonte FROM anomalia_peso_cache ORDER BY timestamp DESC LIMIT 1"""
        )
        row = cursor.fetchone()
    finally:
        conn.close()
    if row:
        return AnomaliaPesoData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            alertas_json=row["alertas_json"],
            fonte=row["fonte"],
        )
    return None


@dataclass
class RadarInflexaoData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "yfinance"


@dataclass
class RadarShortSqueezeData:
    timestamp: datetime
    alertas_json: str
    fonte: str


def save_radar_inflexao_data(data: RadarInflexaoData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO radar_inflexao_cache (timestamp, alertas_json, fonte)
        VALUES (?, ?, ?)
        """,
        (
            data.timestamp.isoformat(),
            data.alertas_json,
            data.fonte,
        ),
    )
    conn.commit()
    conn.close()


def get_latest_radar_inflexao_data() -> RadarInflexaoData | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT timestamp, alertas_json, fonte
            FROM radar_inflexao_cache
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()

    if row:
        return RadarInflexaoData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            alertas_json=row["alertas_json"],
            fonte=row["fonte"],
        )
    return None


@dataclass
class RadarCongestionamentoAtivo:
    ticker: str
    bandwidth: float
    sparkline_path: str


@dataclass
class RadarCongestionamentoData:
    timestamp: datetime
    alertas_json: str
    fonte: str

    @property
    def alertas(self) -> list[RadarCongestionamentoAtivo]:
        import json

        try:
            raw = json.loads(self.alertas_json)
            return [RadarCongestionamentoAtivo(**a) for a in raw]
        except (json.JSONDecodeError, TypeError):
            return []

    @property
    def coletado_em(self) -> str:
        from datetime import timezone, timedelta

        BRT = timezone(timedelta(hours=-3))
        return self.timestamp.astimezone(BRT).strftime("%d/%m/%Y %H:%M:%S")


def save_radar_congestionamento_data(alertas: list[dict], fonte: str) -> None:
    from datetime import timezone
    import json

    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cursor.execute(
        "INSERT INTO radar_congestionamento_cache (timestamp, alertas_json, fonte) VALUES (?, ?, ?)",
        (now, json.dumps(alertas), fonte),
    )
    conn.commit()
    conn.close()


def get_latest_radar_congestionamento_data() -> RadarCongestionamentoData | None:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT timestamp, alertas_json, fonte FROM radar_congestionamento_cache ORDER BY timestamp DESC LIMIT 1"
        )
        row = cursor.fetchone()
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()

    if row:
        return RadarCongestionamentoData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            alertas_json=row["alertas_json"],
            fonte=row["fonte"],
        )
    return None


def save_radar_short_squeeze_data(data: RadarShortSqueezeData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO radar_short_squeeze_cache (timestamp, alertas_json, fonte)
        VALUES (?, ?, ?)
        """,
        (
            data.timestamp.isoformat(),
            data.alertas_json,
            data.fonte,
        ),
    )
    conn.commit()
    conn.close()


def get_latest_radar_short_squeeze_data() -> RadarShortSqueezeData | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT timestamp, alertas_json, fonte
            FROM radar_short_squeeze_cache
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()

    if row:
        return RadarShortSqueezeData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            alertas_json=row["alertas_json"],
            fonte=row["fonte"],
        )
    return None
