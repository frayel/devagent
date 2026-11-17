from typing import Any


def build_sparkline(
    valores: list[float], referencia: float | None = None
) -> dict[str, Any] | None:
    """Pontos de uma linha em viewBox 0 0 200 48 (desenhada no servidor).

    Com `referencia` (spec 175), o valor entra na escala, para a linha
    horizontal dele nunca sair do desenho, e o `y` dele volta em
    `referencia_y`. Sem ela, a saída é a mesma de sempre.
    """
    if not valores or len(valores) < 2:
        return None
    escala = list(valores) + ([referencia] if referencia is not None else [])
    menor, maior = float(min(escala)), float(max(escala))
    if maior - menor < 1e-6:
        centro = (maior + menor) / 2
        menor, maior = centro - 5, centro + 5
    passo = 200 / (len(valores) - 1)

    def y(v: float) -> float:
        return round(44 - (v - menor) / (maior - menor) * 40, 1)

    pontos = " ".join(f"{round(i * passo, 1)},{y(v)}" for i, v in enumerate(valores))
    saida: dict[str, Any] = {
        "pontos": pontos,
        "ultimo_x": 200,
        "ultimo_y": y(valores[-1]),
    }
    if referencia is not None:
        saida["referencia_y"] = y(referencia)
    return saida
