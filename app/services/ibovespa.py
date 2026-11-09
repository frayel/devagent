from typing import Any
from datetime import datetime, timezone, timedelta
import json

from app.collectors.ibovespa import LIMIAR_PCT_REVISAO, LIMIAR_PONTOS_REVISAO
from app.database import get_latest_ibovespa_data


def get_ibovespa_view_data(agora: datetime | None = None) -> dict[str, Any] | None:
    data = get_latest_ibovespa_data()
    if not data:
        return None

    brt = timezone(timedelta(hours=-3))
    dt_brt = data.timestamp.astimezone(brt)
    if agora is None:
        agora_brt = datetime.now(timezone.utc).astimezone(brt).date()
    else:
        agora_brt = agora.astimezone(brt).date()

    if dt_brt.date() == agora_brt:
        titulo = "Ibovespa hoje"
    else:
        titulo = "Ibovespa"

    # Carimbo em America/Sao_Paulo (dd/mm/aaaa HH:MM BRT, sem segundos conforme spec 134)
    time_formatted = dt_brt.strftime("%d/%m/%Y %H:%M BRT")

    if not data.previous_close or data.previous_close <= 0:
        variacao_indisponivel = True
        revisao_variacao = False
        variation_pts = None
        variation_percent = None
        variation_formatted = None
        variation_percent_formatted = None
        is_positive = False
        is_negative = False
        variation_raw = 0.0
    else:
        variacao_indisponivel = False
        variation_pts = data.current_price - data.previous_close
        variation_percent = (variation_pts / data.previous_close) * 100
        revisao_variacao = (
            abs(variation_percent) > LIMIAR_PCT_REVISAO
            or abs(variation_pts) >= LIMIAR_PONTOS_REVISAO
        )
        is_positive = variation_pts > 0
        is_negative = variation_pts < 0
        variation_raw = variation_pts

        variation_formatted = f"{int(variation_pts):,}".replace(",", ".")
        variation_percent_formatted = f"{variation_percent:.2f}%".replace(".", ",")

        if variation_pts > 0:
            variation_formatted = f"+{variation_formatted}"
            variation_percent_formatted = f"+{variation_percent_formatted}"

    # format strings for view
    current_formatted = f"{int(data.current_price):,}".replace(",", ".")

    # calculate moving averages formatting and signals
    mm21_formatted = None
    mm21_signal = None
    if data.mm21 is not None:
        mm21_formatted = f"{int(data.mm21):,}".replace(",", ".")
        if data.current_price > data.mm21:
            mm21_signal = "Alta"
        elif data.current_price < data.mm21:
            mm21_signal = "Baixa"
        else:
            mm21_signal = "Neutra"

    mm200_formatted = None
    mm200_signal = None
    if data.mm200 is not None:
        mm200_formatted = f"{int(data.mm200):,}".replace(",", ".")
        if data.current_price > data.mm200:
            mm200_signal = "Alta"
        elif data.current_price < data.mm200:
            mm200_signal = "Baixa"
        else:
            mm200_signal = "Neutra"

    history_dict = {}
    resumo_serie = ""
    if data.history_json:
        try:
            history_dict = json.loads(data.history_json)
            if "closes" in history_dict and history_dict["closes"]:
                closes = history_dict["closes"]
                primeiro = closes[0]
                ultimo = closes[-1]
                qtd = len(closes)
                var_periodo = (ultimo / primeiro - 1) * 100
                sinal = (
                    "alta"
                    if var_periodo > 0
                    else "baixa"
                    if var_periodo < 0
                    else "estável"
                )

                primeiro_fmt = f"{int(primeiro):,}".replace(",", ".")
                ultimo_fmt = f"{int(ultimo):,}".replace(",", ".")
                var_fmt = f"{abs(var_periodo):.1f}%".replace(".", ",")

                resumo_serie = f"Ibovespa nos últimos {qtd} pregões: de {primeiro_fmt} a {ultimo_fmt}, {sinal} de {var_fmt}"
        except json.JSONDecodeError:
            pass

    return {
        "titulo": titulo,
        "current_price": current_formatted,
        "variation": variation_formatted,
        "variation_percent": variation_percent_formatted,
        "variation_pts": variation_pts,
        "variation_pct": variation_percent,
        "variation_raw": variation_raw,
        "variacao_indisponivel": variacao_indisponivel,
        "revisao_variacao": revisao_variacao,
        "is_positive": is_positive,
        "is_negative": is_negative,
        "time": time_formatted,
        "history_dict": history_dict,
        "resumo_serie": resumo_serie,
        "fonte": data.fonte,
        "mm21": mm21_formatted,
        "mm21_signal": mm21_signal,
        "mm200": mm200_formatted,
        "mm200_signal": mm200_signal,
        "mm21_dist_pct": distancia_da_media(data.current_price, data.mm21),
        "mm200_dist_pct": distancia_da_media(data.current_price, data.mm200),
        "pregao": getattr(data, "pregao_data", None),
    }


def distancia_da_media(preco: float | None, media: float | None) -> float | None:
    """Quanto o índice está acima (+) ou abaixo (−) da média, em % (spec 026)."""
    if preco is None or not media:
        return None
    return (preco / media - 1) * 100
