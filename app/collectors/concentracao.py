import json
import logging
from datetime import datetime, timezone
from app.database import ConcentracaoData, save_concentracao_data
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
    "ELET3": 0.03,
    "BBAS3": 0.03,
}


def fetch_yfinance() -> ConcentracaoData | None:
    symbols = ",".join([f"{t}.SA" for t in TICKERS_PESOS.keys()]) + ",%5EBVSP"
    url = f"https://query1.finance.yahoo.com/v7/finance/spark?symbols={symbols}&range=5d&interval=1d"
    try:
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

        ibov = history_map["^BVSP"]
        ibov_var_pct = (ibov["current"] - ibov["prev"]) / ibov["prev"]

        if abs(ibov_var_pct) < 0.001:
            return ConcentracaoData(
                timestamp=datetime.now(timezone.utc),
                resumo_json=json.dumps(
                    {
                        "estado": "estavel",
                        "mensagem": "Ibovespa estável, sem concentração definida.",
                    }
                ),
                top3_json="[]",
                fonte=mt5.fonte_efetiva("yfinance"),
            )

        ibov_var_pts = ibov["current"] - ibov["prev"]
        direcao_ibov = 1 if ibov_var_pts > 0 else -1

        contribs = []
        for ticker, peso in TICKERS_PESOS.items():
            if ticker in history_map:
                t_data = history_map[ticker]
                t_var_pct = (t_data["current"] - t_data["prev"]) / t_data["prev"]
                t_pts = t_var_pct * peso * ibov["prev"]
                if (direcao_ibov > 0 and t_pts > 0) or (direcao_ibov < 0 and t_pts < 0):
                    contribs.append({"ticker": ticker, "pontos": t_pts, "peso": peso})

        contribs.sort(key=lambda x: abs(x["pontos"]), reverse=True)

        soma_pts = 0
        acoes_50_pct = 0
        pts_alvo = abs(ibov_var_pts) * 0.5
        for c in contribs:
            soma_pts += abs(c["pontos"])
            acoes_50_pct += 1
            if soma_pts >= pts_alvo:
                break

        if acoes_50_pct == 0:
            acoes_50_pct = len(contribs)

        direcao_str = "alta" if direcao_ibov > 0 else "queda"
        perc_fmt = (
            min(100, int((soma_pts / abs(ibov_var_pts)) * 100))
            if abs(ibov_var_pts) > 0
            else 0
        )

        acoes_str = "1 ação" if acoes_50_pct == 1 else f"apenas {acoes_50_pct} ações"
        mensagem = f"Dos {abs(int(ibov_var_pts))} pontos de {direcao_str} do índice, {perc_fmt}% vieram de {acoes_str}."

        return ConcentracaoData(
            timestamp=datetime.now(timezone.utc),
            resumo_json=json.dumps({"estado": "concentrado", "mensagem": mensagem}),
            top3_json=json.dumps(contribs[:3]),
            fonte=mt5.fonte_efetiva("yfinance"),
        )
    except Exception as e:
        logger.error(f"Erro no coletor concentracao: {e}")
        return None


def collect_and_save() -> None:
    data = fetch_yfinance()
    if data:
        save_concentracao_data(data)
