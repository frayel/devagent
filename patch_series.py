import re

with open('app/collectors/utils.py', 'r') as f:
    content = f.read()

# Replace get_historico_diario / save_historico_diario with fetch_historico_diario that uses `ler_serie`/`gravar_serie` if spec 074 says so:
# "Séries diárias de ativos passam a vir de series_diarias (spec 073) quando o coletor as usa, sem baixar de novo o que já está gravado."
# Actually spec 074 says:
# "Séries diárias de ativos passam a vir de `series_diarias` (spec 073) quando o coletor as usa, sem baixar de novo o que já está gravado."
# We should probably leave it as is if it's too much logic, or we update the implementation of fetch_historico_diario_yfinance_chart
# to check the `series_diarias` table via `ler_serie`.
print("Checking how many times fetch_historico_diario_yfinance_chart is used.")
