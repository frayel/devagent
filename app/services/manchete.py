from __future__ import annotations

import json
from typing import Any

# Enum único de humor da manchete (Spec 140)
ALTA_AMPLA = "alta_ampla"
BAIXA_AMPLA = "baixa_ampla"
MISTO = "misto"
SEM_DIRECAO = "sem_direcao"
INDISPONIVEL = "indisponivel"

HUMORES_VALIDOS = {ALTA_AMPLA, BAIXA_AMPLA, MISTO, SEM_DIRECAO, INDISPONIVEL}


class Manchete(str):
    """Objeto manchete que se comporta como string e expõe humor e texto."""

    humor: str
    texto: str

    def __new__(cls, texto: str, humor: str):
        if humor not in HUMORES_VALIDOS:
            raise ValueError(f"Humor inválido: {humor}")
        obj = super().__new__(cls, texto)
        obj.humor = humor
        obj.texto = texto
        return obj

    def __repr__(self) -> str:
        return f"Manchete({self.texto!r}, humor={self.humor!r})"


def gerar_manchete(
    ibovespa_data: dict[str, Any] | None,
    highlights_data: dict[str, Any] | None,
    apetite_risco_data: dict[str, Any] | None,
    motores_data: Any | None = None,
) -> Manchete:
    """Gera a manchete do mercado e o humor segundo a Spec 140."""
    # Regra 1: Sem Ibovespa, ou variação indisponível
    if not ibovespa_data or not highlights_data:
        return Manchete("Resumo do mercado indisponível no momento.", INDISPONIVEL)

    if (
        ibovespa_data.get("variacao_indisponivel") is True
        or ibovespa_data.get("estado") == "indisponivel"
    ):
        return Manchete("Resumo do mercado indisponível no momento.", INDISPONIVEL)

    variacao_pct = ibovespa_data.get("variacao_pct")
    is_positive = ibovespa_data.get("is_positive")
    if is_positive is None and variacao_pct is not None:
        is_positive = variacao_pct > 0
    elif is_positive is not None and variacao_pct is None:
        variacao_pct = 1.0 if is_positive else -1.0

    if variacao_pct is None and is_positive is None:
        return Manchete("Resumo do mercado indisponível no momento.", INDISPONIVEL)

    # Regra 2: Pregão do Ibovespa, da dispersão ou dos motores diferentes entre si
    pregao_ibov = ibovespa_data.get("pregao") or ibovespa_data.get("pregao_data")
    pregao_highs = highlights_data.get("pregao") or highlights_data.get("pregao_data")
    pregao_motores = None
    if isinstance(motores_data, dict):
        pregao_motores = motores_data.get("pregao") or motores_data.get("pregao_data")
    elif hasattr(motores_data, "pregao_data"):
        pregao_motores = getattr(motores_data, "pregao_data")

    pregoes = [p for p in (pregao_ibov, pregao_highs, pregao_motores) if p]
    if len(set(pregoes)) > 1:
        return Manchete(
            "Os painéis não estão no mesmo pregão; a leitura do dia fica suspensa.",
            INDISPONIVEL,
        )

    # Regra 8: Variação do índice igual a zero
    if variacao_pct is not None and abs(variacao_pct) < 1e-9 and not is_positive:
        return Manchete("O mercado opera sem direção definida.", SEM_DIRECAO)

    # Regra 3: revisao_variacao verdadeiro -> misto
    revisao_variacao = bool(ibovespa_data.get("revisao_variacao", False))
    if revisao_variacao:
        direcao = "alta" if is_positive else "baixa"
        return Manchete(
            f"O Ibovespa opera em {direcao}, mas o movimento está em revisão.",
            MISTO,
        )

    # Extração de dados da dispersão
    up_count = highlights_data.get("up_count")
    down_count = highlights_data.get("down_count")
    total_count = highlights_data.get("total_count")
    dispersion_pct = highlights_data.get("dispersion_pct")
    fracao_input = highlights_data.get("fracao_em_alta")

    has_counts = (
        up_count is not None
        and down_count is not None
        and total_count is not None
        and total_count > 0
    )
    if (
        has_counts
        and up_count is not None
        and down_count is not None
        and total_count is not None
    ):
        fracao_em_alta = up_count / total_count
        neutral_count = max(0, total_count - (up_count + down_count))
    elif fracao_input is not None:
        fracao_em_alta = float(fracao_input)
        neutral_count = 0
    elif dispersion_pct is not None:
        fracao_em_alta = dispersion_pct / 100.0
        neutral_count = 0
    else:
        fracao_em_alta = 0.50
        neutral_count = 0

    # Regra 4: fracao_em_alta < 0.20 ou > 0.80
    # Abaixo de 20%, o humor não é alta_ampla. Acima de 80%, não é baixa_ampla.
    # Com o índice positivo e fracao_em_alta < 0.20: humor é misto com sinal do índice e contagens.
    if is_positive and fracao_em_alta < 0.20:
        if has_counts:
            if neutral_count > 0:
                texto = (
                    f"O Ibovespa opera em alta, mas apenas {up_count} das {total_count} "
                    f"ações da amostra sobem ({down_count} em baixa, {neutral_count} estáveis)."
                )
            else:
                texto = (
                    f"O Ibovespa opera em alta, mas apenas {up_count} das {total_count} "
                    f"ações da amostra sobem ({down_count} em baixa)."
                )
        else:
            pct_fmt = f"{int(fracao_em_alta * 100)}%"
            texto = f"O Ibovespa opera em alta, mas apenas {pct_fmt} das ações da amostra sobem."
        return Manchete(texto, MISTO)

    if not is_positive and fracao_em_alta > 0.80:
        if has_counts:
            if neutral_count > 0:
                texto = (
                    f"O Ibovespa opera em baixa, apesar de {up_count} das {total_count} "
                    f"ações da amostra subirem ({down_count} em baixa, {neutral_count} estáveis)."
                )
            else:
                texto = (
                    f"O Ibovespa opera em baixa, apesar de {up_count} das {total_count} "
                    f"ações da amostra subirem ({down_count} em baixa)."
                )
        else:
            pct_fmt = f"{int(fracao_em_alta * 100)}%"
            texto = f"O Ibovespa opera em baixa, apesar de {pct_fmt} das ações da amostra subirem."
        return Manchete(texto, MISTO)

    # Extração dos motores
    motores_lista: list[dict[str, Any]] = []
    if isinstance(motores_data, list):
        motores_lista = [m for m in motores_data if isinstance(m, dict)]
    elif isinstance(motores_data, dict):
        if "motores" in motores_data and isinstance(motores_data["motores"], list):
            motores_lista = [m for m in motores_data["motores"] if isinstance(m, dict)]
        else:
            for k, v in motores_data.items():
                if k not in (
                    "pregao",
                    "pregao_data",
                    "timestamp",
                    "fonte",
                ) and isinstance(v, (int, float)):
                    motores_lista.append({"nome": k, "variacao": float(v)})
    elif motores_data is not None and hasattr(motores_data, "motores_json"):
        try:
            raw = json.loads(getattr(motores_data, "motores_json"))
            if isinstance(raw, list):
                motores_lista = raw
        except (json.JSONDecodeError, TypeError):
            motores_lista = []

    motores_com_numero = [
        m
        for m in motores_lista
        if m.get("variacao") is not None and isinstance(m.get("variacao"), (int, float))
    ]
    motores_faltantes = len(motores_com_numero) == 0

    if is_positive:
        motores_opostos = [m for m in motores_com_numero if m["variacao"] < 0]
    else:
        motores_opostos = [m for m in motores_com_numero if m["variacao"] > 0]

    # Regra 5: Conflito de motores (>= 2 motores têm sinal oposto ao do índice)
    conflito_motores = len(motores_opostos) >= 2
    if conflito_motores:
        direcao = "alta" if is_positive else "baixa"
        if has_counts:
            texto = (
                f"O mercado opera em {direcao}, mas os motores setoriais divergem "
                f"({up_count} altas e {down_count} baixas de {total_count} ações)."
            )
        else:
            texto = f"O mercado opera em {direcao}, mas os motores setoriais divergem dos indicadores internos."
        return Manchete(texto, MISTO)

    # Extração de apetite a risco
    estado_risco = None
    if apetite_risco_data:
        if isinstance(apetite_risco_data, dict):
            estado_risco = apetite_risco_data.get("estado")
        elif hasattr(apetite_risco_data, "estado"):
            estado_risco = getattr(apetite_risco_data, "estado")

    # Regra 6: Sem conflito, sem revisão, índice positivo, fracao_em_alta >= 0.50 e Tomando risco
    if is_positive and fracao_em_alta >= 0.50 and estado_risco == "Tomando risco":
        return Manchete(
            "Dia de otimismo generalizado com forte tomada de risco.",
            ALTA_AMPLA,
        )

    # Espelho de baixa da Regra 6
    if not is_positive and fracao_em_alta <= 0.50 and estado_risco == "Defensivo":
        return Manchete(
            "Dia de pessimismo generalizado com postura defensiva.",
            BAIXA_AMPLA,
        )

    # Regra 7: Sinais mistos
    if is_positive:
        texto_base = (
            "O mercado opera em alta, mas os indicadores internos mostram sinais mistos"
        )
    else:
        texto_base = "O mercado opera em baixa, com indicadores internos apresentando sinais mistos"

    complementos = []
    if has_counts:
        complementos.append(
            f"{up_count} altas e {down_count} baixas de {total_count} ações"
        )
    elif fracao_input is not None:
        complementos.append(f"{int(fracao_em_alta * 100)}% em alta")

    # Avisa que faltou motor quando o humor não for o da regra 6 (e motores faltaram)
    if motores_faltantes and (
        motores_data is not None or has_counts or fracao_input is not None
    ):
        complementos.append("motores ausentes")

    if complementos:
        texto = f"{texto_base} ({'; '.join(complementos)})."
    else:
        texto = f"{texto_base}."

    return Manchete(texto, MISTO)
