def gerar_manchete(ibovespa_data, highlights_data, apetite_risco_data):
    if not ibovespa_data or not highlights_data or not apetite_risco_data:
        return "Resumo do mercado indisponível no momento."

    is_ibov_positive = ibovespa_data.get("is_positive", False)

    dispersion_pct = highlights_data.get("dispersion_pct")
    is_maioria_altas = dispersion_pct is not None and dispersion_pct > 50

    estado_risco = apetite_risco_data.get("estado")

    if is_ibov_positive and is_maioria_altas and estado_risco == "Tomando risco":
        return "Dia de otimismo generalizado com forte tomada de risco."
    elif not is_ibov_positive and not is_maioria_altas and estado_risco == "Defensivo":
        return "Dia de pessimismo generalizado com postura defensiva."
    elif is_ibov_positive:
        return "O mercado opera em alta, mas os indicadores internos mostram sinais mistos."
    elif not is_ibov_positive:
        return "O mercado opera em baixa, com indicadores internos apresentando sinais mistos."
    else:
        return "O mercado opera sem direção definida."
