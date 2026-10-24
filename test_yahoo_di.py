import httpx
url = "https://query1.finance.yahoo.com/v7/finance/spark?symbols=DI1F27.SA,DI1F29.SA,^BVSP&range=1mo&interval=1d"
res = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"})
data = res.json()
print([r.get("symbol") for r in data.get("spark", {}).get("result", [])])
