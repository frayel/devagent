import unicodedata
from app.consultor.universo import CARTEIRA_IBOVESPA, MAPA_NOMES_TICKERS

TERMOS_OPINIAO = [
    "recomend",
    "compra",
    "venda",
    "neutr",
    "preco-alvo",
    "preco alvo",
    "carteira",
    "eleva",
    "rebaix",
    "outperform",
    "underperform",
    "overweight",
    "underweight",
    "market perform",
]


def normalizar(texto: str) -> str:
    if not texto:
        return ""
    texto = str(texto).lower()
    return "".join(
        c
        for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def filtrar_materia(titulo: str, descricao: str, conteudo: str) -> list[str]:
    texto_completo = normalizar(f"{titulo} {descricao} {conteudo}")

    tem_opiniao = any(termo in texto_completo for termo in TERMOS_OPINIAO)
    if not tem_opiniao:
        return []

    tickers_encontrados = set()

    for ticker in CARTEIRA_IBOVESPA:
        if ticker.lower() in texto_completo:
            tickers_encontrados.add(ticker)

    for nome, tickers in MAPA_NOMES_TICKERS.items():
        if normalizar(nome) in texto_completo:
            tickers_encontrados.update(tickers)

    return sorted(list(tickers_encontrados))
