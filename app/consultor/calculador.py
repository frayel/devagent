import json
from datetime import timezone, timedelta
from app.database import get_historico_diario
from app.consultor.universo import CARTEIRA_IBOVESPA
from app.consultor.regras import avaliar_ativo


def calcular_consultor():
    ativos = CARTEIRA_IBOVESPA + ["^BVSP"]
    historicos = get_historico_diario(ativos, "1y", "1d", max_age_minutes=15)

    if "^BVSP" not in historicos or not historicos["^BVSP"]:
        raise ValueError("Dados do Ibovespa indisponíveis")

    ibov_data = json.loads(historicos["^BVSP"]["dados_json"])
    ibov_closes = ibov_data.get("closes", [])

    resultados = {"Comprar": [], "Vender": [], "Aguardar": [], "Sem sinal": []}

    from datetime import datetime

    try:
        ts = datetime.fromisoformat(historicos["^BVSP"]["timestamp"])
        timestamp = ts.astimezone(timezone(timedelta(hours=-3))).strftime(
            "%d/%m/%Y %H:%M:%S BRT"
        )
    except Exception:
        timestamp = "-"

    for ticker in CARTEIRA_IBOVESPA:
        if ticker not in historicos:
            resultados["Sem sinal"].append(
                {
                    "ticker": ticker,
                    "fechamento": 0,
                    "regra": "R0 Sem sinal",
                    "motivo": "Sem dados",
                    "gatilho": "-",
                    "fonte": "-",
                    "timestamp": timestamp,
                }
            )
            continue

        dados_json = json.loads(historicos[ticker]["dados_json"])
        closes = dados_json.get("closes", [])
        volumes = dados_json.get("volumes", [])

        if len(closes) < 220:
            resultados["Sem sinal"].append(
                {
                    "ticker": ticker,
                    "fechamento": closes[-1] if closes else 0,
                    "regra": "R0 Sem sinal",
                    "motivo": "Menos de 220 pregões",
                    "gatilho": "-",
                    "fonte": "yfinance",
                    "timestamp": timestamp,
                }
            )
            continue

        avaliacao = avaliar_ativo(ticker, closes, volumes, ibov_closes)
        resultados[avaliacao["decisao"]].append(
            {
                "ticker": ticker,
                "fechamento": closes[-1],
                "regra": avaliacao["regra"],
                "motivo": avaliacao["motivo"],
                "gatilho": avaliacao["gatilho"],
                "fonte": "yfinance",
                "timestamp": timestamp,
            }
        )

    return {"resultados": resultados, "ativos_avaliados": len(CARTEIRA_IBOVESPA)}
