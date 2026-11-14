from typing import Any
from datetime import datetime, timezone, timedelta
import html
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

    history_dict: dict[str, Any] = {}
    resumo_serie = ""
    serie: dict[str, Any] | None = None
    if data.history_json:
        try:
            history_dict = json.loads(data.history_json)
        except json.JSONDecodeError:
            history_dict = {}
        serie = descrever_serie(
            history_dict.get("dates") or [],
            history_dict.get("closes") or [],
            preco=data.current_price,
            fechamento_anterior=(
                data.previous_close
                if data.previous_close and data.previous_close > 0
                else None
            ),
            variacao_pts_fmt=variation_formatted,
            variacao_pct_fmt=variation_percent_formatted,
        )
        if serie:
            resumo_serie = serie["resumo"]

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
        "serie": serie,
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


def _data_br(iso: str) -> str:
    """'2026-11-05' (ou ISO com hora) vira '05/11/2026'; texto estranho sai escapado."""
    try:
        return datetime.fromisoformat(str(iso)[:10]).strftime("%d/%m/%Y")
    except ValueError:
        return html.escape(str(iso))


def _pontos(valor: float) -> str:
    return f"{int(valor):,}".replace(",", ".")


def descrever_serie(
    datas: list[str],
    fechamentos: list[float],
    *,
    preco: float | None = None,
    fechamento_anterior: float | None = None,
    variacao_pts_fmt: str | None = None,
    variacao_pct_fmt: str | None = None,
) -> dict[str, Any] | None:
    """Legenda, resumo, cor e tooltips do gráfico de 30 pregões (spec 145).

    A janela é lida como janela: o retorno e a cor saem do último contra o
    primeiro ponto, e a variação do dia (último contra o fechamento anterior
    do card) só aparece no tooltip do último ponto.
    """
    pares = [
        (d, float(c))
        for d, c in zip(datas, fechamentos)
        if c is not None and c == c and c > 0
    ]
    if len(pares) < 2:
        return None
    primeiro_iso, primeiro = pares[0]
    ultimo_iso, ultimo = pares[-1]
    qtd = len(pares)
    var_periodo = (ultimo / primeiro - 1) * 100
    sinal = "alta" if var_periodo > 0 else "baixa" if var_periodo < 0 else "estável"
    inicio, fim = _data_br(primeiro_iso), _data_br(ultimo_iso)
    var_fmt = f"{abs(var_periodo):.1f}%".replace(".", ",")

    legenda = f"Últimos {qtd} pregões · {inicio} a {fim}"
    resumo = (
        f"Ibovespa nos últimos {qtd} pregões, de {inicio} a {fim}: "
        f"de {_pontos(primeiro)} a {_pontos(ultimo)}, {sinal} de {var_fmt}"
    )

    tooltips = [f"{_data_br(d)}<br><b>{_pontos(c)}</b>" for d, c in pares]
    if fechamento_anterior is not None and variacao_pct_fmt is not None:
        ultimo_preco = preco if preco is not None else ultimo
        tooltips[-1] = (
            f"{fim}<br>Último <b>{_pontos(ultimo_preco)}</b>"
            f"<br>Fechamento anterior {_pontos(fechamento_anterior)}"
            f"<br>Dia {variacao_pts_fmt} pts ({variacao_pct_fmt})"
        )

    return {
        "datas": [d for d, _ in pares],
        "fechamentos": [c for _, c in pares],
        "qtd": qtd,
        "inicio": inicio,
        "fim": fim,
        "fim_iso": str(ultimo_iso)[:10],
        "legenda": legenda,
        "resumo": resumo,
        "var_periodo_pct": var_periodo,
        "periodo_positivo": var_periodo > 0,
        "tooltips": tooltips,
    }
