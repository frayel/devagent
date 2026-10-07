from typing import Any


def build_sparkline(valores: list[float]) -> dict[str, Any] | None:
    """Pontos de uma linha em viewBox 0 0 200 48 (desenhada no servidor)."""
    if not valores or len(valores) < 2:
        return None
    menor, maior = float(min(valores)), float(max(valores))
    if maior - menor < 1e-6:
        centro = (maior + menor) / 2
        menor, maior = centro - 5, centro + 5
    passo = 200 / (len(valores) - 1)

    def y(v: float) -> float:
        return round(44 - (v - menor) / (maior - menor) * 40, 1)

    pontos = " ".join(f"{round(i * passo, 1)},{y(v)}" for i, v in enumerate(valores))
    return {"pontos": pontos, "ultimo_x": 200, "ultimo_y": y(valores[-1])}
