import httpx
import os

token = os.environ.get("BRAPI_TOKEN", "")
if token:
    url = f"https://brapi.dev/api/quote/DI1F27?token={token}"
    res = httpx.get(url)
    print(res.status_code)
    print(res.json())
else:
    print("no token")
