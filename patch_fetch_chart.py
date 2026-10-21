import re

with open('app/collectors/utils.py', 'r') as f:
    content = f.read()

# fetch_historico_diario_yfinance_chart already calls get_historico_diario and save_historico_diario.
# Wait, let me check what get_historico_diario actually does. I printed it before and it does use ler_serie!
# "def get_historico_diario(tickers: list[str], range_str: str, interval: str, max_age_minutes: int = 15) -> dict[str, dict]:"
# "from app.banco import ler_serie"
# So get_historico_diario ALREADY uses ler_serie.
# Let's verify what save_historico_diario does.
