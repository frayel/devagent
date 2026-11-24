"""Pesos das ações no Ibovespa, numa tabela só (spec 194).

Os valores são aproximados, em percentual do índice, e vieram das constantes
que os coletores mantinham à mão (a da Concentração de Ganhos, igual ao texto
do painel Fator Peso Pesado). Não há data de conferência registrada: conferir
com a carteira teórica da B3 é outra spec. A ordem importa: a Concentração
monta a URL do `spark` nela.
"""

from collections.abc import Iterable

PESOS_IBOVESPA: dict[str, float] = {
    "VALE3": 12.0,
    "PETR4": 8.0,
    "ITUB4": 7.0,
    "PETR3": 4.0,
    "BBDC4": 4.0,
    "B3SA3": 3.0,
    "WEGE3": 3.0,
    "ABEV3": 3.0,
    "BBDC3": 3.0,
    "BBAS3": 3.0,
}


def pesos(tickers: Iterable[str]) -> dict[str, float]:
    """Subconjunto da tabela, na ordem pedida; ticker fora dela levanta KeyError."""
    return {t: PESOS_IBOVESPA[t] for t in tickers}


def numero_peso(peso: float) -> str:
    """Peso sem casa decimal quando inteiro (`12`), com vírgula quando não (`4,5`)."""
    if float(peso).is_integer():
        return str(int(peso))
    return f"{peso:g}".replace(".", ",")


def texto_pesos(tabela: dict[str, float]) -> str:
    """`VALE3 12, PETR4 8, BBDC4 4,5`, sem o sufixo `.SA` do ticker."""
    return ", ".join(
        f"{t.removesuffix('.SA')} {numero_peso(p)}" for t, p in tabela.items()
    )
