import json
import statistics
from datetime import datetime, timezone
from app.database import get_historico_diario, save_consultor_confianca
from app.consultor.universo import CARTEIRA_IBOVESPA
from app.consultor.regras import avaliar_ativo


def pre_processar_ativo(data_json):
    data = (
        json.loads(data_json)
        if isinstance(data_json, str)
        else json.loads(data_json.get("dados_json", "{}"))
        if isinstance(data_json, dict) and "dados_json" in data_json
        else data_json
    )
    if "indicators" in data:
        quote = data["indicators"].get("quote", [{}])[0]
        closes = quote.get("close", [])
        volumes = quote.get("volume", [])

        clean_closes = []
        clean_volumes = []
        clean_timestamps = []

        timestamps = data.get("timestamp", [])

        for i in range(min(len(closes), len(timestamps))):
            if closes[i] is not None:
                clean_closes.append(closes[i])
                clean_volumes.append(
                    volumes[i] if i < len(volumes) and volumes[i] is not None else 0
                )
                clean_timestamps.append(timestamps[i])

        return clean_closes, clean_volumes, clean_timestamps
    else:
        return [], [], []


def rodar_backtest():
    ativos = CARTEIRA_IBOVESPA + ["^BVSP"]
    historicos = get_historico_diario(ativos, "2y", "1d", max_age_minutes=60 * 24 * 7)

    if "^BVSP" not in historicos:
        return

    ibov_closes, _, ibov_ts = pre_processar_ativo(
        historicos["^BVSP"]["dados_json"]
        if "dados_json" in historicos["^BVSP"]
        else historicos["^BVSP"]
    )

    if len(ibov_closes) < 220:
        return

    metricas_regras = {}

    for ticker in CARTEIRA_IBOVESPA:
        if ticker not in historicos:
            continue

        closes, volumes, ts = pre_processar_ativo(
            historicos[ticker]["dados_json"]
            if "dados_json" in historicos[ticker]
            else historicos[ticker]
        )

        if len(closes) < 220:
            continue

        ibov_ts_map = {t: i for i, t in enumerate(ibov_ts)}

        for t in range(220, len(closes) - 20):
            ticker_ts = ts[t]

            if ticker_ts not in ibov_ts_map:
                continue

            ibov_t = ibov_ts_map[ticker_ts]

            if ibov_t < 220:
                continue

            closes_t = closes[: t + 1]
            volumes_t = volumes[: t + 1]
            ibov_closes_t = ibov_closes[: ibov_t + 1]

            avaliacao = avaliar_ativo(ticker, closes_t, volumes_t, ibov_closes_t)

            regra = avaliacao["regra"]
            decisao = avaliacao["decisao"]

            if decisao in ("Comprar", "Vender"):
                if regra not in metricas_regras:
                    metricas_regras[regra] = {
                        "disparos": 0,
                        "acertos": 0,
                        "excessos": [],
                    }

                preco_t = closes[t]
                preco_t20 = closes[t + 20]

                ibov_preco_t = ibov_closes[ibov_t]

                ticker_ts20 = ts[t + 20]
                if ticker_ts20 in ibov_ts_map:
                    ibov_t20 = ibov_ts_map[ticker_ts20]
                    ibov_preco_t20 = ibov_closes[ibov_t20]
                else:
                    if ibov_t + 20 < len(ibov_closes):
                        ibov_preco_t20 = ibov_closes[ibov_t + 20]
                    else:
                        continue

                retorno_ativo = (preco_t20 / preco_t) - 1
                retorno_ibov = (ibov_preco_t20 / ibov_preco_t) - 1

                excesso = retorno_ativo - retorno_ibov

                if decisao == "Vender":
                    excesso = -excesso

                acertou = excesso > 0

                metricas_regras[regra]["disparos"] += 1
                if acertou:
                    metricas_regras[regra]["acertos"] += 1
                metricas_regras[regra]["excessos"].append(excesso)

    agora = datetime.now(timezone.utc)
    from datetime import timedelta

    janela_fim = agora - timedelta(days=7)
    janela_inicio = janela_fim - timedelta(days=730)  # 2 years

    str_janela_inicio = janela_inicio.strftime("%Y-%m-%d")
    str_janela_fim = janela_fim.strftime("%Y-%m-%d")

    for regra, stats in metricas_regras.items():
        excesso_mediano = (
            statistics.median(stats["excessos"]) if stats["excessos"] else 0.0
        )
        save_consultor_confianca(
            regra,
            stats["disparos"],
            stats["acertos"],
            excesso_mediano,
            str_janela_inicio,
            str_janela_fim,
            agora,
        )
