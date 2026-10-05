from app.services.manchete import gerar_manchete


def test_manchete_otimismo_generalizado():
    ibov = {"is_positive": True}
    highs = {"dispersion_pct": 60.0}
    risco = {"estado": "Tomando risco"}

    assert (
        gerar_manchete(ibov, highs, risco)
        == "Dia de otimismo generalizado com forte tomada de risco."
    )


def test_manchete_pessimismo_generalizado():
    ibov = {"is_positive": False}
    highs = {"dispersion_pct": 40.0}
    risco = {"estado": "Defensivo"}

    assert (
        gerar_manchete(ibov, highs, risco)
        == "Dia de pessimismo generalizado com postura defensiva."
    )


def test_manchete_sinais_mistos_alta():
    ibov = {"is_positive": True}
    highs = {"dispersion_pct": 40.0}
    risco = {"estado": "Neutro"}

    assert (
        gerar_manchete(ibov, highs, risco)
        == "O mercado opera em alta, mas os indicadores internos mostram sinais mistos."
    )


def test_manchete_sinais_mistos_baixa():
    ibov = {"is_positive": False}
    highs = {"dispersion_pct": 60.0}
    risco = {"estado": "Neutro"}

    assert (
        gerar_manchete(ibov, highs, risco)
        == "O mercado opera em baixa, com indicadores internos apresentando sinais mistos."
    )


def test_manchete_indisponivel():
    assert (
        gerar_manchete(None, None, None) == "Resumo do mercado indisponível no momento."
    )
