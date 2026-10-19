R1_QUEDAS = 5
R1_GATILHO_VOL = 1.5
R3_IFR_MAX = 70
R3_IFR_RECUO = 60
R4_DISTANCIA_MM200 = 0.03
R4_GATILHO_VOL = 1.0
R5_IFR_MIN = 40
R5_IFR_MAX = 65


def calcular_mm(closes: list[float], window: int) -> float | None:
    if len(closes) < window:
        return None
    return sum(closes[-window:]) / window


def calcular_ifr14(closes: list[float]) -> float | None:
    if len(closes) < 15:
        return None
    gains = []
    losses = []
    for i in range(1, 15):
        diff = closes[i] - closes[i - 1]
        gains.append(diff if diff > 0 else 0)
        losses.append(abs(diff) if diff < 0 else 0)
    avg_gain = sum(gains) / 14
    avg_loss = sum(losses) / 14

    for i in range(15, len(closes)):
        diff = closes[i] - closes[i - 1]
        gain = diff if diff > 0 else 0
        loss = abs(diff) if diff < 0 else 0
        avg_gain = (avg_gain * 13 + gain) / 14
        avg_loss = (avg_loss * 13 + loss) / 14

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calcular_fr20(closes: list[float], ibov_closes: list[float]) -> float | None:
    if len(closes) < 21 or len(ibov_closes) < 21:
        return None
    retorno_ativo = (closes[-1] / closes[-21]) - 1
    retorno_ibov = (ibov_closes[-1] / ibov_closes[-21]) - 1
    return (retorno_ativo - retorno_ibov) * 100


def calcular_vol_rel(volumes: list[float]) -> float | None:
    if len(volumes) < 21:
        return None
    media_vol = sum(volumes[-21:-1]) / 20
    if media_vol == 0:
        return None
    return volumes[-1] / media_vol


def calcular_quedas_seguidas(closes: list[float]) -> int:
    quedas = 0
    for i in range(len(closes) - 1, 0, -1):
        if closes[i] < closes[i - 1]:
            quedas += 1
        else:
            break
    return quedas


def avaliar_ativo(
    ticker: str, closes: list[float], volumes: list[float], ibov_closes: list[float]
) -> dict:
    mm21 = calcular_mm(closes, 21)
    mm200 = calcular_mm(closes, 200)
    ifr14 = calcular_ifr14(closes)
    fr20 = calcular_fr20(closes, ibov_closes)
    calcular_vol_rel(volumes)  # noqa: F841
    quedas = calcular_quedas_seguidas(closes)

    if len(closes) >= 5:
        mm21_5d = calcular_mm(closes[:-5], 21)
    else:
        mm21_5d = None

    fechamento = closes[-1] if closes else 0.0

    if quedas >= R1_QUEDAS:
        return {
            "regra": "R1 Faca caindo",
            "decisao": "Aguardar",
            "motivo": f"{quedas} quedas seguidas.",
            "gatilho": f"Primeiro fechamento em alta com VOL_REL >= {R1_GATILHO_VOL:.1f}",
            "mm200": mm200,
        }

    if mm200 and mm21 and fr20 is not None:
        if fechamento < mm200 and mm21 < mm200 and fr20 < 0:
            return {
                "regra": "R2 Tendência de baixa",
                "decisao": "Vender",
                "motivo": f"Preço < MM200 ({mm200:.2f}), MM21 < MM200, FR20 ({fr20:.2f}%) < 0",
                "gatilho": f"Fechamento acima da MM200 (R$ {mm200:.2f})",
                "mm200": mm200,
            }

    if mm200 and mm21 and ifr14 is not None:
        if fechamento > mm200 and mm21 > mm200 and ifr14 > R3_IFR_MAX:
            return {
                "regra": "R3 Esticada",
                "decisao": "Aguardar",
                "motivo": f"Preço > MM200 ({mm200:.2f}), MM21 > MM200, IFR14 ({ifr14:.2f}) > {R3_IFR_MAX}",
                "gatilho": f"Recuo até a MM21 (R$ {mm21:.2f}) ou IFR14 < {R3_IFR_RECUO}",
                "mm200": mm200,
            }

    if mm200 and mm21 and mm21_5d is not None:
        if mm200 * (1 - R4_DISTANCIA_MM200) <= fechamento <= mm200 and mm21 > mm21_5d:
            return {
                "regra": "R4 Rompimento pendente",
                "decisao": "Aguardar",
                "motivo": f"Preço até 3% abaixo da MM200 ({mm200:.2f}) e MM21 subindo",
                "gatilho": f"Fechamento acima da MM200 (R$ {mm200:.2f}) com VOL_REL >= {R4_GATILHO_VOL:.1f}",
                "mm200": mm200,
            }

    if mm200 and mm21 and ifr14 is not None and fr20 is not None:
        if (
            fechamento > mm200
            and mm21 > mm200
            and R5_IFR_MIN <= ifr14 <= R5_IFR_MAX
            and fr20 > 0
        ):
            return {
                "regra": "R5 Tendência de alta saudável",
                "decisao": "Comprar",
                "motivo": f"Preço > MM200 ({mm200:.2f}), MM21 > MM200, {R5_IFR_MIN} <= IFR14 ({ifr14:.2f}) <= {R5_IFR_MAX}, FR20 ({fr20:.2f}%) > 0",
                "gatilho": f"Fechamento abaixo da MM200 (R$ {mm200:.2f})",
                "mm200": mm200,
            }

    return {
        "regra": "R0 Sem sinal",
        "decisao": "Sem sinal",
        "motivo": "Dados insuficientes ou nenhuma regra atendida",
        "gatilho": "-",
        "mm200": mm200,
    }
