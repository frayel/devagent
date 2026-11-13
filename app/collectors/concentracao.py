import json
import logging
from datetime import datetime, timezone
from app.database import (
    ConcentracaoData,
    save_concentracao_data,
    save_concentracao_vendedora_data,
)
from app.collectors import mt5
from app.collectors.utils import fetch_with_retry

logger = logging.getLogger(__name__)

TICKERS_PESOS = {
    "VALE3": 0.12,
    "PETR4": 0.08,
    "ITUB4": 0.07,
    "PETR3": 0.04,
    "BBDC4": 0.04,
    "B3SA3": 0.03,
    "WEGE3": 0.03,
    "ABEV3": 0.03,
    "BBDC3": 0.03,
    "BBAS3": 0.03,
}


ESTAVEL = "Ibovespa estável, sem concentração definida."


def _historico(url: str) -> dict | None:
    """Último fechamento e o anterior de cada símbolo da resposta do `spark`."""
    response = fetch_with_retry(url)
    data = response.json()
    results = data.get("spark", {}).get("result", [])
    if not results:
        return None

    history_map = {}
    for item in results:
        symbol = item.get("symbol", "").replace(".SA", "")
        resp = item.get("response", [])
        if resp and resp[0].get("indicators", {}).get("quote", []):
            closes = resp[0]["indicators"]["quote"][0].get("close", [])
            valid_closes = [c for c in closes if c is not None]
            if len(valid_closes) >= 2:
                history_map[symbol] = {
                    "current": valid_closes[-1],
                    "prev": valid_closes[-2],
                }
    if "^BVSP" not in history_map:
        return None
    return history_map


def _contribuicoes(history_map: dict) -> list[dict]:
    """Pontos teóricos de cada ticker da cesta que tem base e último preço.

    `pontos = variação_da_ação × peso × fechamento_anterior_do_Ibovespa`.
    """
    ibov_prev = history_map["^BVSP"]["prev"]
    contribs = []
    for ticker, peso in TICKERS_PESOS.items():
        t_data = history_map.get(ticker)
        if not t_data or not t_data["prev"]:
            continue
        t_var_pct = (t_data["current"] - t_data["prev"]) / t_data["prev"]
        contribs.append(
            {"ticker": ticker, "pontos": t_var_pct * peso * ibov_prev, "peso": peso}
        )
    return contribs


def _corte_metade(contribs: list[dict]) -> list[dict]:
    """Primeiros nomes (já ordenados) cuja soma em módulo atinge 50% do total."""
    total = sum(abs(c["pontos"]) for c in contribs)
    alvo = total * 0.5
    escolhidos: list[dict] = []
    soma = 0.0
    for c in contribs:
        escolhidos.append(c)
        soma += abs(c["pontos"])
        if soma >= alvo:
            break
    return escolhidos


def _acoes(n: int) -> str:
    return "1 ação" if n == 1 else f"{n} ações"


def _cesta(k: int) -> str:
    return f"{k} de {len(TICKERS_PESOS)} da cesta"


def _estado(estado: str, mensagem: str, linhas: list[dict]) -> ConcentracaoData:
    return ConcentracaoData(
        timestamp=datetime.now(timezone.utc),
        resumo_json=json.dumps({"estado": estado, "mensagem": mensagem}),
        top3_json=json.dumps(linhas),
        fonte=mt5.fonte_efetiva("yfinance"),
    )


def _movimento(history_map: dict) -> tuple[float, float]:
    ibov = history_map["^BVSP"]
    pts = ibov["current"] - ibov["prev"]
    return pts, pts / ibov["prev"]


def fetch_yfinance() -> ConcentracaoData | None:
    """Concentração de Ganhos: só contribuições positivas (spec 142)."""
    symbols = ",".join([f"{t}.SA" for t in TICKERS_PESOS.keys()]) + ",%5EBVSP"
    url = f"https://query1.finance.yahoo.com/v8/finance/spark?symbols={symbols}&range=5d&interval=1d"
    try:
        history_map = _historico(url)
        if history_map is None:
            return None

        ibov_var_pts, ibov_var_pct = _movimento(history_map)
        if abs(ibov_var_pct) < 0.001:
            return _estado("estavel", ESTAVEL, [])

        contribs = _contribuicoes(history_map)
        k = len(contribs)
        positivos = sorted(
            (c for c in contribs if c["pontos"] > 0),
            key=lambda c: c["pontos"],
            reverse=True,
        )
        if not positivos:
            return _estado(
                "vazio",
                f"Nenhuma contribuição positiva na cesta ({_cesta(k)}).",
                [],
            )

        linhas = _corte_metade(positivos)
        n = len(linhas)
        soma = sum(c["pontos"] for c in linhas)
        movimento = abs(ibov_var_pts)
        perc = round(soma / movimento * 100)

        if ibov_var_pts > 0:
            mensagem = (
                f"Dos {int(movimento)} pontos de alta do índice, {perc}% vieram de "
                f"{_acoes(n)} ({_cesta(k)})."
            )
            if perc > 100:
                mensagem += " O restante da cesta compensou o excesso."
        else:
            mensagem = (
                f"O índice caiu {int(movimento)} pontos; {_acoes(n)} somam "
                f"{int(soma)} pontos de ganho que compensam {perc}% desse "
                f"movimento ({_cesta(k)})."
            )
        return _estado("concentrado", mensagem, linhas)
    except Exception as e:
        logger.error(f"Erro no coletor concentracao: {e}")
        return None


def fetch_concentracao_vendedora_yfinance() -> ConcentracaoData | None:
    """Pressão Vendedora: só contribuições negativas (spec 142)."""
    symbols = ",".join([f"{t}.SA" for t in TICKERS_PESOS.keys()]) + ",%5EBVSP"
    url = f"https://query2.finance.yahoo.com/v8/finance/spark?symbols={symbols}&range=5d&interval=1d"
    try:
        history_map = _historico(url)
        if history_map is None:
            return None

        ibov_var_pts, ibov_var_pct = _movimento(history_map)
        if abs(ibov_var_pct) < 0.001:
            return _estado("estavel", ESTAVEL, [])

        contribs = _contribuicoes(history_map)
        k = len(contribs)
        negativos = sorted(
            (c for c in contribs if c["pontos"] < 0), key=lambda c: c["pontos"]
        )
        if not negativos:
            return _estado(
                "vazio",
                f"Nenhuma contribuição negativa na cesta ({_cesta(k)}).",
                [],
            )

        linhas = _corte_metade(negativos)
        n = len(linhas)
        soma = abs(sum(c["pontos"] for c in linhas))
        movimento = abs(ibov_var_pts)
        perc = round(soma / movimento * 100)

        if ibov_var_pts < 0:
            mensagem = (
                f"Dos {int(movimento)} pontos de queda do índice, {perc}% vieram de "
                f"{_acoes(n)} ({_cesta(k)})."
            )
            if perc > 100:
                mensagem += " O restante da cesta compensou o excesso."
        else:
            mensagem = (
                f"O índice subiu {int(movimento)} pontos; {_acoes(n)} somam "
                f"{int(soma)} pontos negativos que seguraram {perc}% dessa alta "
                f"({_cesta(k)})."
            )
        return _estado("vendedora", mensagem, linhas)
    except Exception as e:
        logger.error(f"Erro no coletor concentracao_vendedora: {e}")
        return None


def collect_and_save() -> bool:
    data = fetch_yfinance()
    data_vend = fetch_concentracao_vendedora_yfinance()

    success = False
    if data:
        save_concentracao_data(data)
        success = True
    if data_vend:
        save_concentracao_vendedora_data(data_vend)
        success = True
    return success
