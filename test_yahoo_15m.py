import httpx
url = "https://query1.finance.yahoo.com/v7/finance/spark?symbols=^BVSP&range=5d&interval=15m"
res = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"})
data = res.json()
print([r.get("symbol") for r in data.get("spark", {}).get("result", [])])
