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
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("volatilidade_silenciosa", hoje, "ao_vivo", data.fonte, payload)


def get_latest_volatilidade_silenciosa_data() -> VolatilidadeSilenciosaData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("volatilidade_silenciosa")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return VolatilidadeSilenciosaData(**payload_copy)


@dataclass
class EsforcoResultadoData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "yfinance"


def save_esforco_resultado_data(data: EsforcoResultadoData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot(
        "esforco_resultado",
        hoje,
        "ao_vivo",
        getattr(data, "fonte", "yfinance"),
        payload,
    )


def get_latest_esforco_resultado_data() -> EsforcoResultadoData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("esforco_resultado")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return EsforcoResultadoData(**payload_copy)


def init_db() -> None:
    from app.banco import init_db as init_banco

    init_banco()
    conn = get_connection()
    cursor = conn.cursor()
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

    cursor.executescript("""

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



                ;



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
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = {
        "timestamp": data.timestamp.isoformat(),
        "current_price": data.current_price,
        "previous_close": data.previous_close,
        "history_json": data.history_json,
        "fonte": data.fonte,
        "mm21": data.mm21,
        "mm200": data.mm200,
    }
    gravar_snapshot("ibovespa", hoje, "ao_vivo", data.fonte, payload)


def get_latest_ibovespa_data() -> IbovespaData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("ibovespa")
    if payload:
        return IbovespaData(
            timestamp=datetime.fromisoformat(payload["timestamp"]),
            current_price=payload["current_price"],
            previous_close=payload["previous_close"],
            history_json=payload["history_json"],
            fonte=payload["fonte"],
            mm21=payload.get("mm21"),
            mm200=payload.get("mm200"),
        )
    return None


def save_highlights_data(data: HighlightsData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = {
        "timestamp": data.timestamp.isoformat(),
        "highs_json": data.highs_json,
        "lows_json": data.lows_json,
        "fonte": data.fonte,
        "up_count": data.up_count,
        "down_count": data.down_count,
        "total_count": data.total_count,
    }
    gravar_snapshot("maiores_altas_baixas", hoje, "ao_vivo", data.fonte, payload)


def get_latest_highlights_data() -> HighlightsData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("maiores_altas_baixas")
    if payload:
        return HighlightsData(
            timestamp=datetime.fromisoformat(payload["timestamp"]),
            highs_json=payload["highs_json"],
            lows_json=payload["lows_json"],
            fonte=payload["fonte"],
            up_count=payload.get("up_count"),
            down_count=payload.get("down_count"),
            total_count=payload.get("total_count"),
        )
    return None


def save_volume_alerts_data(data: VolumeAlertsData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("volume_alerts", hoje, "ao_vivo", data.fonte, payload)


def get_latest_volume_alerts_data() -> VolumeAlertsData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("volume_alerts")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return VolumeAlertsData(**payload_copy)


def save_dolar_correlation_data(data: DolarCorrelationData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot(
        "dolar_correlation",
        hoje,
        "ao_vivo",
        getattr(data, "fonte", "yfinance"),
        payload,
    )


def get_latest_dolar_correlation_data() -> DolarCorrelationData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("dolar_correlation")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return DolarCorrelationData(**payload_copy)


def save_fator_mola_data(data: FatorMolaData) -> None:
    from app.banco import gravar_snapshot

    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("fator_mola", data.timestamp.date(), "ao_vivo", data.fonte, payload)


def get_latest_fator_mola_data() -> FatorMolaData | None:
    from app.banco import ler_snapshot

    payload = ler_snapshot("fator_mola")
    if not payload:
        return None
    payload_copy = dict(payload)
    if isinstance(payload_copy.get("timestamp"), str):
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])
    return FatorMolaData(**payload_copy)


init_db()


def save_scanner_capitulacao_data(data: ScannerCapitulacaoData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("scanner_capitulacao", hoje, "ao_vivo", data.fonte, payload)


def get_latest_scanner_capitulacao_data() -> ScannerCapitulacaoData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("scanner_capitulacao")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return ScannerCapitulacaoData(**payload_copy)


def save_forca_relativa_data(data: ForcaRelativaData) -> None:
    from app.banco import gravar_snapshot

    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot(
        "forca_relativa", data.timestamp.date(), "ao_vivo", data.fonte, payload
    )


def get_latest_forca_relativa_data() -> ForcaRelativaData | None:
    from app.banco import ler_snapshot

    payload = ler_snapshot("forca_relativa")
    if not payload:
        return None
    payload_copy = dict(payload)
    if isinstance(payload_copy.get("timestamp"), str):
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])
    return ForcaRelativaData(**payload_copy)


def save_escudo_quedas_data(data: EscudoQuedasData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot(
        "escudo_quedas", hoje, "ao_vivo", getattr(data, "fonte", "yfinance"), payload
    )


def get_latest_escudo_quedas_data() -> EscudoQuedasData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("escudo_quedas")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return EscudoQuedasData(**payload_copy)


def save_coesao_data(data: CoesaoData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("coesao", hoje, "ao_vivo", data.fonte, payload)


def get_latest_coesao_data() -> CoesaoData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("coesao")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return CoesaoData(**payload_copy)


def save_atrasadas_rally_data(data: AtrasadasRallyData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("atrasadas_rally", hoje, "ao_vivo", data.fonte, payload)


def get_latest_atrasadas_rally_data() -> AtrasadasRallyData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("atrasadas_rally")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return AtrasadasRallyData(**payload_copy)


def save_concentracao_data(data: ConcentracaoData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("concentracao", hoje, "ao_vivo", data.fonte, payload)


def save_concentracao_vendedora_data(data: ConcentracaoData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("concentracao_vendedora", hoje, "ao_vivo", data.fonte, payload)


def get_latest_concentracao_vendedora_data() -> ConcentracaoData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("concentracao_vendedora")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return ConcentracaoData(**payload_copy)


def get_latest_concentracao_data() -> ConcentracaoData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("concentracao")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return ConcentracaoData(**payload_copy)


def save_variacao_subita_data(data: VariacaoSubitaData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("variacao_subita", hoje, "ao_vivo", data.fonte, payload)


def get_latest_variacao_subita_data() -> VariacaoSubitaData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("variacao_subita")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return VariacaoSubitaData(**payload_copy)


def save_concentracao_setorial_data(data: ConcentracaoSetorialData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("concentracao_setorial", hoje, "ao_vivo", data.fonte, payload)


def get_latest_concentracao_setorial_data() -> ConcentracaoSetorialData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("concentracao_setorial")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return ConcentracaoSetorialData(**payload_copy)


def save_apetite_risco_data(data: ApetiteRiscoData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("apetite_risco", hoje, "ao_vivo", data.fonte, payload)


def get_latest_apetite_risco_data() -> ApetiteRiscoData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("apetite_risco")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return ApetiteRiscoData(**payload_copy)


def save_rotacao_capital_data(data: RotacaoCapitalData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("rotacao_capital", hoje, "ao_vivo", data.fonte, payload)


def get_latest_rotacao_capital_data() -> RotacaoCapitalData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("rotacao_capital")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return RotacaoCapitalData(**payload_copy)


@dataclass
class FacaCaindoData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "yfinance"


def save_faca_caindo_data(data: FacaCaindoData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot(
        "faca_caindo", hoje, "ao_vivo", getattr(data, "fonte", "yfinance"), payload
    )


def get_latest_faca_caindo_data() -> FacaCaindoData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("faca_caindo")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return FacaCaindoData(**payload_copy)


@dataclass
class CompradoresFundoData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "yfinance"


def save_compradores_fundo_data(data: CompradoresFundoData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("compradores_fundo", hoje, "ao_vivo", data.fonte, payload)


def get_latest_compradores_fundo_data() -> CompradoresFundoData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("compradores_fundo")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return CompradoresFundoData(**payload_copy)


@dataclass
class ArmadilhaAberturaData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "yfinance"


def save_armadilha_abertura_data(data: ArmadilhaAberturaData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("armadilha_abertura", hoje, "ao_vivo", data.fonte, payload)


def get_latest_armadilha_abertura_data() -> ArmadilhaAberturaData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("armadilha_abertura")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return ArmadilhaAberturaData(**payload_copy)


@dataclass
class SobrevivenciaSemanalData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "yfinance"


def save_sobrevivencia_semanal_data(data: SobrevivenciaSemanalData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("sobrevivencia_semanal", hoje, "ao_vivo", data.fonte, payload)


def get_latest_sobrevivencia_semanal_data() -> SobrevivenciaSemanalData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("sobrevivencia_semanal")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return SobrevivenciaSemanalData(**payload_copy)


def save_mare_data(data: MareData) -> None:
    from app.banco import gravar_snapshot

    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("mare", data.timestamp.date(), "ao_vivo", data.fonte, payload)


def get_latest_mare_data() -> MareData | None:
    from app.banco import ler_snapshot

    payload = ler_snapshot("mare")
    if not payload:
        return None
    payload_copy = dict(payload)
    if isinstance(payload_copy.get("timestamp"), str):
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])
    return MareData(**payload_copy)


@dataclass
class AnomaliaPesoData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "yfinance"


def save_anomalia_peso_data(data: AnomaliaPesoData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("anomalia_peso", hoje, "ao_vivo", data.fonte, payload)


def get_latest_anomalia_peso_data() -> AnomaliaPesoData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("anomalia_peso")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return AnomaliaPesoData(**payload_copy)


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
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("radar_inflexao", hoje, "ao_vivo", data.fonte, payload)


def get_latest_radar_inflexao_data() -> RadarInflexaoData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("radar_inflexao")
    if not payload:
        return None
    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])
    return RadarInflexaoData(**payload_copy)


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

        BRT = timezone(timedelta(hours=-3))
        return self.timestamp.astimezone(BRT).strftime("%d/%m/%Y %H:%M:%S BRT")


def save_radar_congestionamento_data(alertas: list[dict], fonte: str) -> None:
    from app.banco import gravar_snapshot
    from datetime import datetime
    import json

    now = datetime.now(timezone.utc)
    hoje = now.date()
    payload = {
        "timestamp": now.isoformat(),
        "alertas_json": json.dumps(alertas),
        "fonte": fonte,
    }
    gravar_snapshot("radar_congestionamento", hoje, "ao_vivo", fonte, payload)


def get_latest_radar_congestionamento_data() -> RadarCongestionamentoData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("radar_congestionamento")
    if not payload:
        return None
    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])
    return RadarCongestionamentoData(**payload_copy)


def save_radar_short_squeeze_data(data: RadarShortSqueezeData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("radar_short_squeeze", hoje, "ao_vivo", data.fonte, payload)


def get_latest_radar_short_squeeze_data() -> RadarShortSqueezeData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("radar_short_squeeze")
    if not payload:
        return None
    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])
    return RadarShortSqueezeData(**payload_copy)


@dataclass
class FalsoRompimentoData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "yfinance"


def save_falso_rompimento_data(data: FalsoRompimentoData) -> None:
    from app.banco import gravar_snapshot

    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot(
        "falso_rompimento", data.timestamp.date(), "ao_vivo", data.fonte, payload
    )


def get_latest_falso_rompimento_data() -> FalsoRompimentoData | None:
    from app.banco import ler_snapshot

    payload = ler_snapshot("falso_rompimento")
    if not payload:
        return None
    payload_copy = dict(payload)
    if isinstance(payload_copy.get("timestamp"), str):
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])
    return FalsoRompimentoData(**payload_copy)


@dataclass
class RadarAbsorcaoCruzadaData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "yfinance"


def save_radar_absorcao_cruzada_data(data: RadarAbsorcaoCruzadaData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("radar_absorcao_cruzada", hoje, "ao_vivo", data.fonte, payload)


def get_latest_radar_absorcao_cruzada_data() -> RadarAbsorcaoCruzadaData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("radar_absorcao_cruzada")
    if not payload:
        return None
    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])
    return RadarAbsorcaoCruzadaData(**payload_copy)


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
    from app.banco import gravar_snapshot

    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot(
        "liquidez_abertura", data.timestamp.date(), "ao_vivo", data.fonte, payload
    )


def get_latest_liquidez_abertura_data() -> LiquidezAberturaData | None:
    from app.banco import ler_snapshot

    payload = ler_snapshot("liquidez_abertura")
    if not payload:
        return None
    payload_copy = dict(payload)
    if isinstance(payload_copy.get("timestamp"), str):
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])
    return LiquidezAberturaData(**payload_copy)


def save_radar_divergencia_volume_data(data: RadarDivergenciaVolumeData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("radar_divergencia_volume", hoje, "ao_vivo", data.fonte, payload)


def get_latest_radar_divergencia_volume_data() -> RadarDivergenciaVolumeData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("radar_divergencia_volume")
    if not payload:
        return None
    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])
    return RadarDivergenciaVolumeData(**payload_copy)


def save_sensibilidade_juros_data(data: SensibilidadeJurosData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("sensibilidade_juros", hoje, "ao_vivo", data.fonte, payload)


def get_latest_sensibilidade_juros_data() -> SensibilidadeJurosData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("sensibilidade_juros")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return SensibilidadeJurosData(**payload_copy)


def save_fator_peso_pesado_data(data: FatorPesoPesadoData) -> None:
    from app.banco import gravar_snapshot

    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot(
        "fator_peso_pesado", data.timestamp.date(), "ao_vivo", data.fonte, payload
    )


def get_latest_fator_peso_pesado_data() -> FatorPesoPesadoData | None:
    from app.banco import ler_snapshot

    payload = ler_snapshot("fator_peso_pesado")
    if not payload:
        return None
    payload_copy = dict(payload)
    if isinstance(payload_copy.get("timestamp"), str):
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])
    return FatorPesoPesadoData(**payload_copy)


def save_motores_indice_data(data: MotoresIndiceData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("motores_indice", hoje, "ao_vivo", data.fonte, payload)


def get_latest_motores_indice_data() -> MotoresIndiceData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("motores_indice")
    if not payload:
        return None
    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])
    return MotoresIndiceData(**payload_copy)


@dataclass
class ClimaGlobalData:
    timestamp: datetime
    sp500_pct: float
    vix_pct: float
    status: str
    fonte: str = "yfinance"


def save_clima_global_data(data: ClimaGlobalData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("clima_global", hoje, "ao_vivo", data.fonte, payload)


def get_latest_clima_global_data() -> ClimaGlobalData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("clima_global")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return ClimaGlobalData(**payload_copy)


def get_latest_relogio_volatilidade_data() -> RelogioVolatilidadeData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("relogio_volatilidade")
    if not payload:
        return None
    payload_copy = payload.copy()
    if "id" not in payload_copy:
        payload_copy["id"] = 0
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])
    return RelogioVolatilidadeData(**payload_copy)


def save_relogio_volatilidade_data(data: RelogioVolatilidadeData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("relogio_volatilidade", hoje, "ao_vivo", data.fonte, payload)


def save_coleta_tempo(painel: str, duracao: float, timestamp: datetime) -> None:
    from app.banco import ler_snapshot, gravar_snapshot

    hoje = timestamp.astimezone(timezone.utc).date()

    payload = ler_snapshot("instrumentacao", hoje) or {
        "tempos": {},
        "vazias": {},
        "rodadas": {},
    }
    if "tempos" not in payload:
        payload["tempos"] = {}
    if "rodadas" not in payload:
        payload["rodadas"] = {}

    payload["tempos"][painel] = duracao
    payload["rodadas"][painel] = payload["rodadas"].get(painel, 0) + 1

    gravar_snapshot("instrumentacao", hoje, "ao_vivo", "sistema", payload)


def save_coleta_vazia(painel: str, timestamp: datetime) -> None:
    from app.banco import ler_snapshot, gravar_snapshot

    hoje = timestamp.astimezone(timezone.utc).date()

    payload = ler_snapshot("instrumentacao", hoje) or {
        "tempos": {},
        "vazias": {},
        "rodadas": {},
    }
    if "vazias" not in payload:
        payload["vazias"] = {}

    payload["vazias"][painel] = payload["vazias"].get(painel, 0) + 1

    gravar_snapshot("instrumentacao", hoje, "ao_vivo", "sistema", payload)


def get_coletas_vazias_count(painel: str) -> int:
    from app.banco import ler_snapshot
    from datetime import datetime as dt

    hoje = dt.now(timezone.utc).astimezone().date()
    payload = ler_snapshot("instrumentacao", hoje)
    if payload and "vazias" in payload:
        return payload["vazias"].get(painel, 0)
    return 0


def get_coletas_vazias_desde(desde: datetime) -> dict[str, int]:
    """Painel → quantas coletas vazias desde `desde` (página /sistema, spec 082)."""
    from app.banco import ler_snapshot
    from datetime import datetime as dt

    hoje = dt.now(timezone.utc).astimezone().date()
    payload = ler_snapshot("instrumentacao", hoje)
    if payload and "vazias" in payload:
        return payload["vazias"]
    return {}


def get_tempos_coleta_desde(desde: datetime) -> dict[str, float]:
    """Painel → duração da coleta mais recente desde `desde`, em segundos (spec 082)."""
    from app.banco import ler_snapshot
    from datetime import datetime as dt

    hoje = dt.now(timezone.utc).astimezone().date()
    payload = ler_snapshot("instrumentacao", hoje)
    if payload and "tempos" in payload:
        return payload["tempos"]
    return {}


def get_rodadas_coleta_desde(desde: datetime) -> dict[str, int]:
    """Painel → quantas coletas rodaram desde `desde` (spec 082)."""
    from app.banco import ler_snapshot
    from datetime import datetime as dt

    hoje = dt.now(timezone.utc).astimezone().date()
    payload = ler_snapshot("instrumentacao", hoje)
    if payload and "rodadas" in payload:
        return payload["rodadas"]
    return {}


@dataclass
class RadarAnomaliasSpreadData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "brapi"


def save_radar_anomalias_spread_data(data: RadarAnomaliasSpreadData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("anomalias_spread", hoje, "ao_vivo", data.fonte, payload)


def get_latest_radar_anomalias_spread_data() -> RadarAnomaliasSpreadData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("anomalias_spread")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return RadarAnomaliasSpreadData(**payload_copy)


def save_concentracao_ordens_data(data: ConcentracaoOrdensData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("concentracao_ordens", hoje, "ao_vivo", data.fonte, payload)


def get_latest_concentracao_ordens_data() -> ConcentracaoOrdensData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("concentracao_ordens")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return ConcentracaoOrdensData(**payload_copy)


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
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot(
        "exaustao_queda", hoje, "ao_vivo", getattr(data, "fonte", "yfinance"), payload
    )


def get_latest_exaustao_queda_data() -> ExaustaoQuedaData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("exaustao_queda")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return ExaustaoQuedaData(**payload_copy)


def save_exaustao_tendencia_data(data: ExaustaoTendenciaData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot(
        "exaustao_tendencia",
        hoje,
        "ao_vivo",
        getattr(data, "fonte", "yfinance"),
        payload,
    )


def get_latest_exaustao_tendencia_data() -> ExaustaoTendenciaData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("exaustao_tendencia")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return ExaustaoTendenciaData(**payload_copy)


@dataclass
class AssimetriaRiscoRetornoData:
    timestamp: datetime
    alertas_json: str
    fonte: str


def save_assimetria_risco_retorno_data(data: AssimetriaRiscoRetornoData) -> None:
    from app.banco import gravar_snapshot

    hoje = data.timestamp.astimezone(timezone.utc).date()
    payload = data.__dict__.copy()
    payload["timestamp"] = payload["timestamp"].isoformat()
    gravar_snapshot("assimetria_risco_retorno", hoje, "ao_vivo", data.fonte, payload)


def get_latest_assimetria_risco_retorno_data() -> AssimetriaRiscoRetornoData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("assimetria_risco_retorno")
    if not payload:
        return None

    payload_copy = payload.copy()
    if "timestamp" in payload_copy:
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])

    return AssimetriaRiscoRetornoData(**payload_copy)


def get_historico_diario(
    tickers: list[str], range_str: str, interval: str, max_age_minutes: int = 15
) -> dict[str, dict]:
    from app.banco import ler_serie
    from datetime import date, timedelta

    result = {}
    hoje = date.today()
    inicio = hoje - timedelta(days=365 * 2)  # max

    for ticker in tickers:
        barras = ler_serie(ticker, inicio, hoje)
        if barras:
            closes = [b.get("close") for b in barras]
            quote_dict = {"close": closes}
            if "open" in barras[0]:
                quote_dict["open"] = [b.get("open", 0) for b in barras]
                quote_dict["high"] = [b.get("high", 0) for b in barras]
                quote_dict["low"] = [b.get("low", 0) for b in barras]
                quote_dict["volume"] = [b.get("volume", 0) for b in barras]

            spark_like_item = {
                "symbol": ticker,
                "timestamp": [1] * len(closes),
                "indicators": {"quote": [quote_dict]},
            }
            result[ticker] = spark_like_item

    return result


def save_historico_diario(
    ticker: str, range_str: str, interval: str, dados_json: str, timestamp: datetime
) -> None:
    from app.banco import gravar_serie
    import json

    try:
        dados = json.loads(dados_json)
        quote = dados.get("indicators", {}).get("quote", [{}])[0]
        closes = quote.get("close", [])

        times = dados.get("timestamp", [])
        if not closes or not times:
            return

        from datetime import datetime as dt, timezone

        barras = []
        for i in range(len(closes)):
            if closes[i] is None:
                continue
            data = dt.fromtimestamp(times[i], tz=timezone.utc).strftime("%Y-%m-%d")
            barra = {"data": data, "close": closes[i]}
            if "open" in quote and quote["open"][i] is not None:
                barra["open"] = quote["open"][i]
                barra["high"] = quote["high"][i]
                barra["low"] = quote["low"][i]
                barra["volume"] = quote["volume"][i]
            barras.append(barra)

        gravar_serie(ticker, barras)
    except Exception:
        pass


def save_divergencia_ibov_dolar(
    divergencia_detectada: bool, correlacao: float, timestamp: datetime
) -> None:
    from app.banco import gravar_snapshot

    hoje = timestamp.astimezone(timezone.utc).date()
    payload = {
        "timestamp": timestamp.isoformat(),
        "divergencia_detectada": divergencia_detectada,
        "correlacao": correlacao,
    }
    gravar_snapshot("divergencia_ibov_dolar", hoje, "ao_vivo", "yfinance", payload)


def get_divergencia_ibov_dolar() -> dict | None:
    from app.banco import ler_snapshot

    return ler_snapshot("divergencia_ibov_dolar")


def save_radar_anomalia_fechamento_data(alertas_json: str, fonte: str) -> None:
    from app.banco import gravar_snapshot
    from app.calendario import pregao_corrente
    from datetime import datetime, timezone as tz

    agora = datetime.now(tz.utc)
    hoje = pregao_corrente(agora)
    payload = {
        "alertas_json": alertas_json,
        "fonte": fonte,
        "timestamp": agora.isoformat(),
    }
    gravar_snapshot("radar_anomalia_fechamento", hoje, "ao_vivo", fonte, payload)


def get_latest_radar_anomalia_fechamento_data() -> RadarAnomaliaFechamentoData | None:
    from app.banco import ler_snapshot
    from datetime import datetime, timezone as tz

    snapshot = ler_snapshot("radar_anomalia_fechamento")
    if not snapshot:
        return None

    ts_str = snapshot.get("timestamp")
    if ts_str:
        ts = datetime.fromisoformat(ts_str)
    else:
        ts = datetime.now(tz.utc)

    return RadarAnomaliaFechamentoData(
        timestamp=ts,
        alertas_json=snapshot.get("alertas_json", "[]"),
        fonte=snapshot.get("fonte", ""),
    )


def save_consultor_confianca(
    regra: str,
    disparos: int,
    acertos: int,
    excesso_mediano: float,
    janela_inicio: str,
    janela_fim: str,
    atualizado_em: datetime,
) -> None:
    from app.banco import ler_snapshot, gravar_snapshot
    from app.calendario import pregao_corrente
    from datetime import datetime, timezone as tz

    agora = datetime.now(tz.utc)
    hoje = pregao_corrente(agora)
    snapshot = ler_snapshot("consultor_confianca")
    payload = snapshot if snapshot else {}
    payload[regra] = {
        "disparos": disparos,
        "acertos": acertos,
        "excesso_mediano": excesso_mediano,
        "janela_inicio": janela_inicio,
        "janela_fim": janela_fim,
        "atualizado_em": atualizado_em.isoformat(),
    }
    gravar_snapshot("consultor_confianca", hoje, "ao_vivo", "sistema", payload)


def get_consultor_confianca() -> dict[str, dict]:
    from app.banco import ler_snapshot
    from datetime import datetime

    snapshot = ler_snapshot("consultor_confianca")
    if not snapshot:
        return {}

    for k, v in snapshot.items():
        if "atualizado_em" in v and isinstance(v["atualizado_em"], str):
            v["atualizado_em"] = datetime.fromisoformat(v["atualizado_em"])

    return snapshot


@dataclass
class ExaustaoAltaData:
    timestamp: datetime
    alertas_json: str
    fonte: str = "yfinance"


def save_exaustao_alta_data(data: ExaustaoAltaData) -> None:
    from datetime import datetime, timezone
    from app.banco import gravar_snapshot

    hoje = datetime.now(timezone.utc).date()
    payload = {
        "timestamp": data.timestamp.isoformat(),
        "alertas_json": data.alertas_json,
        "fonte": getattr(data, "fonte", "yfinance"),
    }
    gravar_snapshot(
        "exaustao_alta", hoje, "ao_vivo", getattr(data, "fonte", "yfinance"), payload
    )


def get_latest_exaustao_alta_data() -> ExaustaoAltaData | None:
    from app.banco import ler_snapshot
    from datetime import datetime

    payload = ler_snapshot("exaustao_alta")
    if not payload:
        return None
    payload_copy = payload.copy()
    if isinstance(payload_copy.get("timestamp"), str):
        payload_copy["timestamp"] = datetime.fromisoformat(payload_copy["timestamp"])
    return ExaustaoAltaData(**payload_copy)
