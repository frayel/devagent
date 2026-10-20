import sqlite3
import json
from dataclasses import dataclass
import os
from datetime import datetime, timezone, timedelta

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
class SensibilidadeJurosData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "yfinance"


@dataclass
@dataclass
class RadarAnomaliaFechamentoData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "yfinance"


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


@dataclass
class ConcentracaoOrdensData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "brapi"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@dataclass
class RelogioVolatilidadeData:
    id: int
    timestamp: datetime
    alertas_json: str
    fonte: str


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


@dataclass
class EsforcoResultadoData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "yfinance"


def save_esforco_resultado_data(data: EsforcoResultadoData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO esforco_resultado_cache (timestamp, alertas_json, fonte) VALUES (?, ?, ?)",
        (data.timestamp.isoformat(), data.alertas_json, data.fonte),
    )
    conn.commit()
    conn.close()


def get_latest_esforco_resultado_data() -> EsforcoResultadoData | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT timestamp, alertas_json, fonte FROM esforco_resultado_cache ORDER BY timestamp DESC LIMIT 1"
        )
        row = cursor.fetchone()
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()
    if row:
        return EsforcoResultadoData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            alertas_json=row["alertas_json"],
            fonte=row["fonte"],
        )
    return None


def init_db() -> None:
    conn = get_connection()
    try:
        conn.execute(
            "ALTER TABLE consultor_confianca_regras ADD COLUMN janela_inicio TEXT"
        )
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute(
            "ALTER TABLE consultor_confianca_regras ADD COLUMN janela_fim TEXT"
        )
        conn.commit()
    except Exception:
        pass
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS radar_anomalia_fechamento_cache (
            timestamp TEXT PRIMARY KEY,
            alertas_json TEXT,
            fonte TEXT
        );
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_radar_anomalia_fechamento_timestamp ON radar_anomalia_fechamento_cache (timestamp DESC);
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS divergencia_ibov_dolar_cache (
            timestamp TEXT PRIMARY KEY,
            divergencia_detectada INTEGER,
            correlacao REAL
        );
        """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_divergencia_ibov_dolar_timestamp ON divergencia_ibov_dolar_cache (timestamp DESC);
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consultor_confianca_regras (
            regra TEXT PRIMARY KEY,
            disparos INTEGER,
            acertos INTEGER,
            excesso_mediano REAL,
            janela_inicio TEXT,
            janela_fim TEXT,
            atualizado_em TEXT
        );
    """)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS historico_diario_cache (
            ticker TEXT,
            range_str TEXT,
            interval TEXT,
            dados_json TEXT,
            timestamp TEXT,
            PRIMARY KEY (ticker, range_str, interval)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS assimetria_risco_retorno_cache (
            timestamp TEXT PRIMARY KEY,
            alertas_json TEXT NOT NULL,
            fonte TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_assimetria_risco_retorno_cache_timestamp ON assimetria_risco_retorno_cache (timestamp DESC)"
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS exaustao_tendencia_cache (
            timestamp TEXT PRIMARY KEY,
            alertas_json TEXT NOT NULL,
            fonte TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_exaustao_tendencia_timestamp ON exaustao_tendencia_cache (timestamp DESC)"
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS concentracao_ordens_cache (
            timestamp TEXT PRIMARY KEY,
            alertas_json TEXT NOT NULL,
            fonte TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_concentracao_ordens_cache_timestamp ON concentracao_ordens_cache (timestamp DESC)"
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS anomalias_spread_cache (
            timestamp TEXT PRIMARY KEY,
            alertas_json TEXT NOT NULL,
            fonte TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_anomalias_spread_cache_timestamp ON anomalias_spread_cache (timestamp DESC)"
    )

    cursor.executescript("""

        CREATE TABLE IF NOT EXISTS relogio_volatilidade_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            alertas_json TEXT NOT NULL,
            fonte TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_relogio_volatilidade_timestamp ON relogio_volatilidade_cache(timestamp DESC);
        CREATE TABLE IF NOT EXISTS instrumentacao_coleta_vazia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            painel TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_instrumentacao_coleta_vazia_timestamp ON instrumentacao_coleta_vazia(timestamp DESC);
        CREATE TABLE IF NOT EXISTS instrumentacao_coleta_tempo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            painel TEXT NOT NULL,
            duracao REAL NOT NULL,
            timestamp TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_instrumentacao_coleta_tempo_timestamp ON instrumentacao_coleta_tempo(timestamp DESC);


        CREATE TABLE IF NOT EXISTS clima_global_cache (
            timestamp TEXT NOT NULL,
            sp500_pct REAL NOT NULL,
            vix_pct REAL NOT NULL,
            status TEXT NOT NULL,
            fonte TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_clima_global_cache_timestamp ON clima_global_cache(timestamp DESC);


        CREATE TABLE IF NOT EXISTS falso_rompimento_cache (
            timestamp TEXT NOT NULL,
            alertas_json TEXT NOT NULL,
            fonte TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_falso_rompimento_cache_timestamp ON falso_rompimento_cache(timestamp DESC);

                CREATE TABLE IF NOT EXISTS sensibilidade_juros_cache (
            timestamp TEXT NOT NULL,
            alertas_json TEXT NOT NULL,
            fonte TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_sensibilidade_juros_cache_timestamp ON sensibilidade_juros_cache(timestamp DESC);


        CREATE TABLE IF NOT EXISTS radar_absorcao_cruzada_cache (
            timestamp TEXT NOT NULL,
            alertas_json TEXT NOT NULL,
            fonte TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_radar_absorcao_cruzada_cache_timestamp ON radar_absorcao_cruzada_cache(timestamp DESC);
        CREATE TABLE IF NOT EXISTS liquidez_abertura_cache (
            timestamp TEXT NOT NULL,
            alertas_json TEXT NOT NULL,
            fonte TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_liquidez_abertura_timestamp ON liquidez_abertura_cache(timestamp DESC);

        CREATE TABLE IF NOT EXISTS radar_divergencia_volume_cache (
            timestamp TEXT NOT NULL,
            alertas_json TEXT NOT NULL,
            fonte TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_radar_divergencia_volume_cache_timestamp ON radar_divergencia_volume_cache(timestamp DESC);
        CREATE TABLE IF NOT EXISTS esforco_resultado_cache (
            timestamp TEXT,
            alertas_json TEXT,
            fonte TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_esforco_resultado_timestamp ON esforco_resultado_cache(timestamp DESC);

        CREATE TABLE IF NOT EXISTS radar_congestionamento_cache (
            timestamp TEXT,
            alertas_json TEXT,
            fonte TEXT
        );

        CREATE TABLE IF NOT EXISTS motores_indice_cache (
            timestamp TEXT PRIMARY KEY,
            motores_json TEXT NOT NULL,
            fonte TEXT DEFAULT 'yfinance'
        );
        CREATE INDEX IF NOT EXISTS idx_motores_indice_cache_timestamp ON motores_indice_cache(timestamp DESC);
        CREATE TABLE IF NOT EXISTS fator_peso_pesado_cache (
            timestamp DATETIME PRIMARY KEY,
            proporcao REAL,
            mercado_lateral BOOLEAN,
            resumo_json TEXT,
            fonte TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_fator_peso_pesado_timestamp ON fator_peso_pesado_cache(timestamp DESC);
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

    cursor.executescript("""

        CREATE TABLE IF NOT EXISTS concentracao_vendedora_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            resumo_json TEXT NOT NULL,
            top3_json TEXT NOT NULL,
            fonte TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_concentracao_vendedora_timestamp ON concentracao_vendedora_cache (timestamp DESC);

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

    conn.execute("""
        CREATE TABLE IF NOT EXISTS exaustao_queda_cache (
            timestamp TEXT PRIMARY KEY,
            alertas_json TEXT NOT NULL,
            fonte TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_exaustao_queda_cache_timestamp
        ON exaustao_queda_cache(timestamp DESC)
    """)

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS consultor_fila_materias (
            guid TEXT PRIMARY KEY,
            titulo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            conteudo TEXT NOT NULL,
            data_publicacao TEXT NOT NULL,
            link TEXT NOT NULL,
            tickers_citados TEXT NOT NULL,
            criado_em TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_consultor_fila_materias_criado_em
        ON consultor_fila_materias(criado_em DESC);
    """)
    try:
        cursor.execute(
            "ALTER TABLE consultor_fila_materias ADD COLUMN processada INTEGER DEFAULT 0"
        )
    except Exception:
        pass
    cursor.executescript("""
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
            extraida_em TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS consultor_opinioes_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL,
            motivo TEXT,
            desde TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS consultor_llm_uso (
            data TEXT PRIMARY KEY,
            chamadas INTEGER NOT NULL
        );
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


def save_concentracao_vendedora_data(data: ConcentracaoData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO concentracao_vendedora_cache (timestamp, resumo_json, top3_json, fonte)
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


def get_latest_concentracao_vendedora_data() -> ConcentracaoData | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT timestamp, resumo_json, top3_json, fonte
        FROM concentracao_vendedora_cache
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
        cursor = conn.cursor()
        cursor.execute(
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
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT timestamp, valor, fluxo, calma, volume, historico_json, fonte
            FROM mare_cache
            ORDER BY timestamp DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
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

        try:
            raw = json.loads(self.alertas_json)
            return [RadarCongestionamentoAtivo(**a) for a in raw]
        except (json.JSONDecodeError, TypeError):
            return []

    @property
    def coletado_em(self) -> str:
        from datetime import timezone

        BRT = timezone(timedelta(hours=-3))
        return self.timestamp.astimezone(BRT).strftime("%d/%m/%Y %H:%M:%S BRT")


def save_radar_congestionamento_data(alertas: list[dict], fonte: str) -> None:
    from datetime import timezone

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
            alertas_json=row["alertas_json"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
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


@dataclass
class FalsoRompimentoData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "yfinance"


def save_falso_rompimento_data(data: FalsoRompimentoData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO falso_rompimento_cache (timestamp, alertas_json, fonte) VALUES (?, ?, ?)",
        (data.timestamp.isoformat(), data.alertas_json, data.fonte),
    )
    conn.commit()
    conn.close()


def get_latest_falso_rompimento_data() -> FalsoRompimentoData | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT timestamp, alertas_json, fonte FROM falso_rompimento_cache ORDER BY timestamp DESC LIMIT 1"
        )
        row = cursor.fetchone()
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()
    if row:
        return FalsoRompimentoData(
            timestamp=datetime.fromisoformat(row[0]),
            alertas_json=row[1],
            fonte=row[2],
        )
    return None


@dataclass
class RadarAbsorcaoCruzadaData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "yfinance"


def save_radar_absorcao_cruzada_data(data: RadarAbsorcaoCruzadaData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO radar_absorcao_cruzada_cache (timestamp, alertas_json, fonte) VALUES (?, ?, ?)",
        (data.timestamp.isoformat(), data.alertas_json, data.fonte),
    )
    conn.commit()
    conn.close()


def get_latest_radar_absorcao_cruzada_data() -> RadarAbsorcaoCruzadaData | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT timestamp, alertas_json, fonte FROM radar_absorcao_cruzada_cache ORDER BY timestamp DESC LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return RadarAbsorcaoCruzadaData(
            timestamp=datetime.fromisoformat(row[0]),
            alertas_json=row[1],
            fonte=row[2],
        )
    return None


@dataclass
class LiquidezAberturaData:
    timestamp: datetime
    alertas_json: str
    fonte: str


@dataclass
class RadarDivergenciaVolumeData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "yfinance"


@dataclass
class MotoresIndiceData:
    timestamp: datetime
    motores_json: str
    fonte: str = "yfinance"


@dataclass
class FatorPesoPesadoData:
    timestamp: datetime
    proporcao: float
    mercado_lateral: bool
    resumo_json: str
    fonte: str = "yfinance"


def save_liquidez_abertura_data(data: LiquidezAberturaData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO liquidez_abertura_cache (timestamp, alertas_json, fonte) VALUES (?, ?, ?)",
        (data.timestamp.isoformat(), data.alertas_json, data.fonte),
    )
    conn.commit()
    conn.close()


def get_latest_liquidez_abertura_data() -> LiquidezAberturaData | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT timestamp, alertas_json, fonte FROM liquidez_abertura_cache ORDER BY timestamp DESC LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return LiquidezAberturaData(
            timestamp=datetime.fromisoformat(row[0]),
            alertas_json=row[1],
            fonte=row[2],
        )
    return None


def save_radar_divergencia_volume_data(data: RadarDivergenciaVolumeData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO radar_divergencia_volume_cache (timestamp, alertas_json, fonte) VALUES (?, ?, ?)",
        (data.timestamp.isoformat(), data.alertas_json, data.fonte),
    )
    conn.commit()
    conn.close()


def get_latest_radar_divergencia_volume_data() -> RadarDivergenciaVolumeData | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT timestamp, alertas_json, fonte FROM radar_divergencia_volume_cache ORDER BY timestamp DESC LIMIT 1"
        )
        row = cursor.fetchone()
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()
    if row:
        return RadarDivergenciaVolumeData(
            timestamp=datetime.fromisoformat(row[0]),
            alertas_json=row[1],
            fonte=row[2],
        )
    return None


def save_sensibilidade_juros_data(data: SensibilidadeJurosData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sensibilidade_juros_cache (timestamp, alertas_json, fonte) VALUES (?, ?, ?)",
        (data.timestamp.isoformat(), data.alertas_json, data.fonte),
    )
    conn.commit()
    conn.close()


def get_latest_sensibilidade_juros_data() -> SensibilidadeJurosData | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT timestamp, alertas_json, fonte FROM sensibilidade_juros_cache ORDER BY timestamp DESC LIMIT 1"
        )
        row = cursor.fetchone()
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()
    if row:
        return SensibilidadeJurosData(
            timestamp=datetime.fromisoformat(row[0]),
            alertas_json=row[1],
            fonte=row[2],
        )
    return None


def save_fator_peso_pesado_data(data: FatorPesoPesadoData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO fator_peso_pesado_cache (timestamp, proporcao, mercado_lateral, resumo_json, fonte) VALUES (?, ?, ?, ?, ?)",
        (
            data.timestamp,
            data.proporcao,
            data.mercado_lateral,
            data.resumo_json,
            data.fonte,
        ),
    )
    conn.commit()
    conn.close()


def get_latest_fator_peso_pesado_data() -> FatorPesoPesadoData | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT timestamp, proporcao, mercado_lateral, resumo_json, fonte FROM fator_peso_pesado_cache ORDER BY timestamp DESC LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return FatorPesoPesadoData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            proporcao=row["proporcao"],
            mercado_lateral=bool(row["mercado_lateral"]),
            resumo_json=row["resumo_json"],
            fonte=row["fonte"],
        )
    return None


def save_motores_indice_data(data: MotoresIndiceData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO motores_indice_cache (timestamp, motores_json, fonte)
        VALUES (?, ?, ?)
    """,
        (data.timestamp.isoformat(), data.motores_json, data.fonte),
    )
    conn.commit()
    conn.close()


def get_latest_motores_indice_data() -> MotoresIndiceData | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, motores_json, fonte
        FROM motores_indice_cache
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()

    if row:
        return MotoresIndiceData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            motores_json=row["motores_json"],
            fonte=row["fonte"],
        )
    return None


@dataclass
class ClimaGlobalData:
    timestamp: datetime
    sp500_pct: float
    vix_pct: float
    status: str
    fonte: str = "yfinance"


def save_clima_global_data(data: ClimaGlobalData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO clima_global_cache (timestamp, sp500_pct, vix_pct, status, fonte) VALUES (?, ?, ?, ?, ?)",
        (
            data.timestamp.isoformat(),
            data.sp500_pct,
            data.vix_pct,
            data.status,
            data.fonte,
        ),
    )
    conn.commit()
    conn.close()


def get_latest_clima_global_data() -> ClimaGlobalData | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT timestamp, sp500_pct, vix_pct, status, fonte FROM clima_global_cache ORDER BY timestamp DESC LIMIT 1"
        )
        row = cursor.fetchone()
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()
    if row:
        return ClimaGlobalData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            sp500_pct=row["sp500_pct"],
            vix_pct=row["vix_pct"],
            status=row["status"],
            fonte=row["fonte"],
        )
    return None


def get_latest_relogio_volatilidade_data() -> RelogioVolatilidadeData | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM relogio_volatilidade_cache ORDER BY timestamp DESC LIMIT 1"
    )
    row = cursor.fetchone()
    if row:
        return RelogioVolatilidadeData(
            id=row[0],
            timestamp=datetime.fromisoformat(row[1]),
            alertas_json=row[2],
            fonte=row[3],
        )
    return None


def save_coleta_tempo(painel: str, duracao: float, timestamp: datetime) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO instrumentacao_coleta_tempo (painel, duracao, timestamp) VALUES (?, ?, ?)",
        (painel, duracao, timestamp.isoformat()),
    )
    conn.commit()


def save_coleta_vazia(painel: str, timestamp: datetime) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO instrumentacao_coleta_vazia (painel, timestamp) VALUES (?, ?)",
        (painel, timestamp.isoformat()),
    )
    conn.commit()
    conn.close()


def get_coletas_vazias_count(painel: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM instrumentacao_coleta_vazia WHERE painel = ?", (painel,)
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0


def get_coletas_vazias_desde(desde: datetime) -> dict[str, int]:
    """Painel → quantas coletas vazias desde `desde` (página /sistema, spec 082)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT painel, COUNT(*) FROM instrumentacao_coleta_vazia "
            "WHERE timestamp >= ? GROUP BY painel",
            (desde.isoformat(),),
        ).fetchall()
    finally:
        conn.close()
    return {r[0]: r[1] for r in rows}


def get_tempos_coleta_desde(desde: datetime) -> dict[str, float]:
    """Painel → duração da coleta mais recente desde `desde`, em segundos (spec 082)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT painel, duracao FROM instrumentacao_coleta_tempo t "
            "WHERE timestamp >= ? AND timestamp = ("
            "  SELECT MAX(timestamp) FROM instrumentacao_coleta_tempo u "
            "  WHERE u.painel = t.painel)",
            (desde.isoformat(),),
        ).fetchall()
    finally:
        conn.close()
    return {r[0]: float(r[1]) for r in rows}


def get_rodadas_coleta_desde(desde: datetime) -> dict[str, int]:
    """Painel → quantas coletas rodaram desde `desde` (spec 082)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT painel, COUNT(*) FROM instrumentacao_coleta_tempo "
            "WHERE timestamp >= ? GROUP BY painel",
            (desde.isoformat(),),
        ).fetchall()
    finally:
        conn.close()
    return {r[0]: r[1] for r in rows}


def diagnostico() -> dict:
    """Tipo, tamanho e latência do banco em uso (página /sistema, spec 082)."""
    import time

    info: dict = {
        "tipo": "SQLite",
        "database_url": bool(os.environ.get("DATABASE_URL", "").strip()),
    }
    inicio = time.perf_counter()
    try:
        conn = get_connection()
        try:
            tabelas = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'"
            ).fetchone()[0]
        finally:
            conn.close()
    except Exception as e:  # noqa: BLE001 - a página mostra o erro
        info["erro"] = f"{type(e).__name__}: {e}"[:200]
        return info
    info["latencia_ms"] = round((time.perf_counter() - inicio) * 1000)
    info["tabelas"] = tabelas
    try:
        tamanho = os.path.getsize(DB_PATH)
        info["tamanho"] = (
            f"{tamanho / 1_048_576:.1f} MB".replace(".", ",")
            if tamanho >= 1_048_576
            else f"{tamanho // 1024} KB"
        )
    except OSError:
        info["tamanho"] = "?"
    return info


@dataclass
class RadarAnomaliasSpreadData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "brapi"


def save_radar_anomalias_spread_data(data: RadarAnomaliasSpreadData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO anomalias_spread_cache (timestamp, alertas_json, fonte) VALUES (?, ?, ?)",
        (data.timestamp.isoformat(), data.alertas_json, data.fonte),
    )
    conn.commit()
    conn.close()


def get_latest_radar_anomalias_spread_data() -> RadarAnomaliasSpreadData | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT timestamp, alertas_json, fonte FROM anomalias_spread_cache ORDER BY timestamp DESC LIMIT 1"
        )
        row = cursor.fetchone()
    except Exception:
        return None
    finally:
        conn.close()
    if row:
        return RadarAnomaliasSpreadData(
            timestamp=datetime.fromisoformat(row[0]), alertas_json=row[1], fonte=row[2]
        )
    return None


def save_concentracao_ordens_data(data: ConcentracaoOrdensData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO concentracao_ordens_cache (timestamp, alertas_json, fonte) VALUES (?, ?, ?)",
        (data.timestamp.isoformat(), data.alertas_json, data.fonte),
    )
    conn.commit()
    conn.close()


def get_latest_concentracao_ordens_data() -> ConcentracaoOrdensData | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT timestamp, alertas_json, fonte FROM concentracao_ordens_cache ORDER BY timestamp DESC LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return ConcentracaoOrdensData(
            timestamp=datetime.fromisoformat(row[0]), alertas_json=row[1], fonte=row[2]
        )
    return None


@dataclass
class ExaustaoQuedaData:
    timestamp: datetime
    alertas_json: str
    fonte: str


@dataclass
class ExaustaoTendenciaData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "yfinance"


def save_exaustao_queda_data(data: ExaustaoQuedaData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO exaustao_queda_cache (timestamp, alertas_json, fonte) VALUES (?, ?, ?)",
        (data.timestamp.isoformat(), data.alertas_json, data.fonte),
    )
    conn.commit()
    conn.close()


def get_latest_exaustao_queda_data() -> ExaustaoQuedaData | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT timestamp, alertas_json, fonte FROM exaustao_queda_cache ORDER BY timestamp DESC LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return ExaustaoQuedaData(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            alertas_json=row["alertas_json"],
            fonte=row["fonte"],
        )
    return None


def save_exaustao_tendencia_data(data: ExaustaoTendenciaData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO exaustao_tendencia_cache (timestamp, alertas_json, fonte) VALUES (?, ?, ?)",
        (data.timestamp.isoformat(), data.alertas_json, data.fonte),
    )
    conn.commit()
    conn.close()


def get_latest_exaustao_tendencia_data() -> ExaustaoTendenciaData | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT timestamp, alertas_json, fonte FROM exaustao_tendencia_cache ORDER BY timestamp DESC LIMIT 1"
        )
        row = cursor.fetchone()
    except Exception:
        return None
    finally:
        conn.close()
    if row:
        return ExaustaoTendenciaData(
            timestamp=datetime.fromisoformat(row[0]), alertas_json=row[1], fonte=row[2]
        )
    return None


@dataclass
class AssimetriaRiscoRetornoData:
    timestamp: datetime
    alertas_json: str
    fonte: str


def save_assimetria_risco_retorno_data(data: AssimetriaRiscoRetornoData) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO assimetria_risco_retorno_cache (timestamp, alertas_json, fonte) VALUES (?, ?, ?)",
        (data.timestamp.isoformat(), data.alertas_json, data.fonte),
    )
    conn.commit()
    conn.close()


def get_latest_assimetria_risco_retorno_data() -> AssimetriaRiscoRetornoData | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT timestamp, alertas_json, fonte FROM assimetria_risco_retorno_cache ORDER BY timestamp DESC LIMIT 1"
        )
        row = cursor.fetchone()
    except Exception:
        return None
    finally:
        conn.close()
    if row:
        return AssimetriaRiscoRetornoData(
            timestamp=datetime.fromisoformat(row[0]), alertas_json=row[1], fonte=row[2]
        )
    return None


def get_historico_diario(
    tickers: list[str], range_str: str, interval: str, max_age_minutes: int = 15
) -> dict[str, dict]:
    conn = get_connection()
    cursor = conn.cursor()
    placeholders = ",".join(["?"] * len(tickers))
    try:
        cursor.execute(
            f"SELECT ticker, dados_json, timestamp FROM historico_diario_cache WHERE ticker IN ({placeholders}) AND range_str = ? AND interval = ?",
            (*tickers, range_str, interval),
        )
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()

    agora = datetime.now(timezone.utc)
    result = {}
    for row in rows:
        ts = datetime.fromisoformat(row[2])
        if (agora - ts).total_seconds() <= max_age_minutes * 60:
            result[row[0]] = json.loads(row[1])
    return result


def save_historico_diario(
    ticker: str, range_str: str, interval: str, dados_json: str, timestamp: datetime
) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO historico_diario_cache (ticker, range_str, interval, dados_json, timestamp) VALUES (?, ?, ?, ?, ?)",
        (ticker, range_str, interval, dados_json, timestamp.isoformat()),
    )
    conn.commit()
    conn.close()


def save_divergencia_ibov_dolar(
    divergencia_detectada: bool, correlacao: float, timestamp: datetime
) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO divergencia_ibov_dolar_cache (timestamp, divergencia_detectada, correlacao)
        VALUES (?, ?, ?)
        """,
        (timestamp.isoformat(), int(divergencia_detectada), correlacao),
    )
    conn.commit()
    conn.close()


def get_divergencia_ibov_dolar() -> dict | None:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT timestamp, divergencia_detectada, correlacao
        FROM divergencia_ibov_dolar_cache
        ORDER BY timestamp DESC
        LIMIT 1
        """
    )
    row = cursor.fetchone()
    if row:
        res = {
            "timestamp": row["timestamp"],
            "divergencia_detectada": bool(row["divergencia_detectada"]),
            "correlacao": row["correlacao"],
        }
        conn.close()
        return res
    conn.close()
    return None


def save_radar_anomalia_fechamento_data(alertas_json: str, fonte: str) -> None:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now_str = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            "INSERT INTO radar_anomalia_fechamento_cache (timestamp, alertas_json, fonte) VALUES (?, ?, ?)",
            (now_str, alertas_json, fonte),
        )
        conn.commit()
    finally:
        conn.close()


def get_latest_radar_anomalia_fechamento_data() -> RadarAnomaliaFechamentoData | None:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT timestamp, alertas_json, fonte FROM radar_anomalia_fechamento_cache ORDER BY timestamp DESC LIMIT 1"
        )
        row = cursor.fetchone()
    except Exception:
        return None
    finally:
        conn.close()
    if row:
        return RadarAnomaliaFechamentoData(
            timestamp=datetime.fromisoformat(row[0]),
            alertas_json=row[1],
            fonte=row[2],
        )
    return None


def save_consultor_confianca_regra(
    regra: str,
    disparos: int,
    acertos: int,
    excesso_mediano: float,
    janela_inicio: str,
    janela_fim: str,
    atualizado_em: datetime,
) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO consultor_confianca_regras (regra, disparos, acertos, excesso_mediano, janela_inicio, janela_fim, atualizado_em) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            regra,
            disparos,
            acertos,
            excesso_mediano,
            janela_inicio,
            janela_fim,
            atualizado_em.isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def get_consultor_confianca_regras() -> dict[str, dict]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT regra, disparos, acertos, excesso_mediano, janela_inicio, janela_fim, atualizado_em FROM consultor_confianca_regras"
        )
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()

    result = {}
    for row in rows:
        result[row[0]] = {
            "disparos": row[1],
            "acertos": row[2],
            "excesso_mediano": row[3],
            "janela_inicio": row[4],
            "janela_fim": row[5],
            "atualizado_em": datetime.fromisoformat(row[6]),
        }
    return result
