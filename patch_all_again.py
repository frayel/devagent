import re

# 1. Update database.py
with open("app/database.py", "r") as f:
    content = f.read()

func_code = """
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
"""
if "get_latest_relogio_volatilidade_data" not in content:
    content += "\n" + func_code

dataclass_code = """
@dataclass
class RelogioVolatilidadeData:
    id: int
    timestamp: datetime
    alertas_json: str
    fonte: str
"""
if "RelogioVolatilidadeData" not in content:
    content = re.sub(
        r"(@dataclass\nclass ScannerCapitulacaoData:)",
        dataclass_code + r"\n\n\1",
        content,
    )

create_table_sql = """
        CREATE TABLE IF NOT EXISTS relogio_volatilidade_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            alertas_json TEXT NOT NULL,
            fonte TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_relogio_volatilidade_timestamp ON relogio_volatilidade_cache(timestamp DESC);
"""
if "CREATE TABLE IF NOT EXISTS relogio_volatilidade_cache" not in content:
    content = re.sub(
        r"(        CREATE TABLE IF NOT EXISTS clima_global_cache \()",
        create_table_sql + r"\n\1",
        content,
    )

with open("app/database.py", "w") as f:
    f.write(content)


# 2. Add collectors/relogio_volatilidade.py
with open("app/collectors/relogio_volatilidade.py", "w") as f:
    f.write("""import json
import logging
from datetime import datetime, timezone

from app.database import get_connection

logger = logging.getLogger(__name__)

def collect_and_save() -> bool:
    try:
        from app.collectors.utils import fetch_with_retry
        # We need intraday data for ^BVSP
        url = "https://query1.finance.yahoo.com/v8/finance/chart/^BVSP?range=1d&interval=15m"
        data = fetch_with_retry(url)

        if not data:
            return False

        result = data.json().get("chart", {}).get("result", [])
        if not result:
            return False

        quote = result[0].get("indicators", {}).get("quote", [])
        if not quote:
            return False

        highs = quote[0].get("high", [])
        lows = quote[0].get("low", [])

        # Calculate amplitudes
        amplitudes = []
        for h, low in zip(highs, lows):
            if h is not None and low is not None:
                amplitudes.append(h - low)

        if not amplitudes:
            return False

        # Find peak
        max_amp = max(amplitudes)

        alertas = {
            "ticker": "^BVSP",
            "variacao": result[0].get("meta", {}).get("regularMarketPrice", 0) - result[0].get("meta", {}).get("previousClose", 0),
            "amplitude_percentual": (max_amp / result[0].get("meta", {}).get("previousClose", 1)) * 100,
            "minima": result[0].get("meta", {}).get("regularMarketDayLow", 0),
            "maxima": result[0].get("meta", {}).get("regularMarketDayHigh", 0)
        }

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM relogio_volatilidade_cache")
        cursor.execute(
            \"\"\"
            INSERT INTO relogio_volatilidade_cache (timestamp, alertas_json, fonte)
            VALUES (?, ?, ?)
            \"\"\",
            (datetime.now(timezone.utc), json.dumps(alertas), "yfinance")
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error collecting relogio_volatilidade: {e}")
        return False
""")

# 3. Update agendador.py
with open("app/agendador.py", "r") as f:
    content = f.read()

if "import app.collectors.relogio_volatilidade" not in content:
    content = re.sub(
        r"(import app\.collectors\.radar_congestionamento\n)",
        r"\1import app.collectors.relogio_volatilidade\n",
        content,
        count=1,
    )

if '"relogio_volatilidade"' not in content:
    content = content.replace(
        '"clima_global",\n    ):',
        '"clima_global",\n        "relogio_volatilidade",\n    ):',
    )

with open("app/agendador.py", "w") as f:
    f.write(content)


# 4. Update test_agendador.py
with open("tests/test_agendador.py", "r") as f:
    content = f.read()

new_line = '    monkeypatch.setattr("app.collectors.relogio_volatilidade.collect_and_save", lambda: True)\n'
if new_line not in content:
    content = re.sub(
        r"(    monkeypatch\.setattr\(\"app\.collectors\.radar_congestionamento\.collect_and_save\", lambda: True\)\n)",
        r"\g<1>" + new_line,
        content,
    )

if '"relogio_volatilidade"' not in content:
    content = re.sub(
        r'("dolar_correlation",\n)',
        r'\1            "sensibilidade_juros",\n            "motores_indice",\n            "relogio_volatilidade",\n',
        content,
    )

with open("tests/test_agendador.py", "w") as f:
    f.write(content)
