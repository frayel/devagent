import os
import httpx

token = os.environ.get("BRAPI_TOKEN")
UNIVERSO = 100
url = f"https://brapi.dev/api/quote/list?type=stock&sortBy=volume&sortOrder=desc&limit={UNIVERSO}"
if token:
    url += f"&token={token}"

try:
    resp = httpx.get(url, timeout=10.0)
    data = resp.json()
    stocks = data.get("stocks", [])

    TICKERS = [
        "PETR4",
        "VALE3",
        "ITUB4",
        "BBDC4",
        "B3SA3",
        "ABEV3",
        "ELET3",
        "RENT3",
        "WEGE3",
        "BBAS3",
        "ITSA4",
        "SUZB3",
        "BPAC11",
        "RADL3",
        "EQTL3",
        "CSAN3",
        "PRIO3",
        "RDOR3",
        "RAIL3",
        "SBSP3",
        "VIVT3",
        "CMIG4",
        "LREN3",
        "CPLE6",
        "UGPA3",
        "ENEV3",
        "TIMS3",
        "TOTS3",
        "EGIE3",
        "HAPV3",
    ]

    mapping = {}
    for item in stocks:
        if item["stock"] in TICKERS:
            mapping[item["stock"]] = item.get("sector")

    for t in TICKERS:
        print(f'"{t}": "{mapping.get(t, "Unknown")}",')

except Exception as e:
    print(f"Error: {e}")
