import re
with open('app/collectors/utils.py', 'r') as f:
    content = f.read()

func_pattern = r'def fetch_historico_diario_yfinance_chart.*?return spark_like_item.*?except httpx\.HTTPError as e:.*?return None'

res = re.search(func_pattern, content, re.DOTALL)
if res:
    print("Found fetch_historico_diario_yfinance_chart")
