def _calcular_excesso(
    preco_inicial: float,
    preco_final: float,
    ibov_inicial: float,
    ibov_final: float,
) -> float:
    retorno_ativo = (preco_final / preco_inicial) - 1.0
    retorno_ibov = (ibov_final / ibov_inicial) - 1.0
    return retorno_ativo - retorno_ibov
