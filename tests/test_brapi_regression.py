import glob
import re


def test_no_comma_in_brapi_urls():
    collectors = glob.glob("app/collectors/*.py")
    for filepath in collectors:
        if filepath.endswith("brapi.py"):
            continue
        with open(filepath, "r") as f:
            content = f.read()
            assert not re.search(r"https://brapi\.dev/api/quote/\{[^\}]+\}", content), (
                f"Encontrado concatenação de múltiplos tickers em {filepath}"
            )
            assert not re.search(r"https://brapi\.dev/api/quote/\w+%2C", content), (
                f"Encontrado concatenação com %2C em {filepath}"
            )
