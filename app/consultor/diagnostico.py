"""Diagnóstico das opiniões do Consultor, igual na página e no JSON (spec 198)."""

import logging
from datetime import datetime
from typing import Any

from app.consultor import armazenamento

logger = logging.getLogger(__name__)


def _vazio(codigo: str, motivo: str = "") -> dict[str, Any]:
    return {
        "codigo": codigo,
        "motivo": motivo,
        "desde": "",
        "ultima_extracao_em": "",
        "materias_processadas": 0,
        "opinioes_gravadas": 0,
        "descartadas": 0,
        "fila_pendentes": None,
    }


def diagnostico_de_opinioes(dados: dict | None, pregao_passado: bool) -> dict:
    """O diagnóstico da lista de opiniões, com as oito chaves de sempre.

    No pregão passado o status da extração é de agora, não daquele dia: sai
    `pregao_passado`, sem consultar a fila. Nunca levanta.
    """
    if pregao_passado:
        return _vazio("pregao_passado")
    try:
        dados_dict = dados if isinstance(dados, dict) else {}
        status_data = dados_dict.get("opinioes_status") or {}
        has_opinions = len(dados_dict.get("opinioes_recentes") or []) > 0
        status = status_data.get("status", "ok")
        never_extracted = not bool(status_data.get("ultima_extracao_em"))
        descartadas = status_data.get("descartadas", 0) or 0
        fila_pendentes = armazenamento.contar_fila_pendente()

        codigo = "aguardando"
        if status == "sem_chave":
            codigo = "sem_chave"
        elif status == "cota":
            codigo = "cota"
        elif status in ("erro", "invalido"):
            codigo = "erro"
        elif never_extracted:
            codigo = "aguardando"
        elif status == "ok":
            if fila_pendentes > 0:
                codigo = "fila"
            elif descartadas > 0 and not has_opinions:
                codigo = "descartadas"
            elif not has_opinions:
                codigo = "sem_materias"
            else:
                codigo = "ok"

        return {
            "codigo": codigo,
            "motivo": status_data.get("motivo", "") or "",
            "desde": status_data.get("desde", "") or "",
            "ultima_extracao_em": status_data.get("ultima_extracao_em", "") or "",
            "materias_processadas": status_data.get("materias_processadas", 0) or 0,
            "opinioes_gravadas": status_data.get("opinioes_gravadas", 0) or 0,
            "descartadas": descartadas,
            "fila_pendentes": fila_pendentes,
        }
    except Exception:
        logger.exception("Diagnóstico de opiniões indisponível")
        return _vazio("erro", "diagnóstico indisponível")


def _idade_vazia() -> dict[str, Any]:
    return {"desde": None, "horas": None, "texto": ""}


def idade_da_fila(agora: datetime) -> dict[str, Any]:
    """Há quanto tempo a matéria mais antiga da fila espera (spec 202).

    Devolve sempre `desde`, `horas` e `texto`; fila vazia, data ilegível ou
    erro de banco dão o dicionário vazio. Nunca levanta.
    """
    try:
        from app.services.sistema import _dt, ha_quanto

        desde = armazenamento.fila_pendente_desde()
        inicio = _dt(desde)
        if desde is None or inicio is None:
            return _idade_vazia()
        segundos = max(0.0, (agora - inicio).total_seconds())
        return {
            "desde": desde,
            "horas": round(segundos / 3600, 1),
            "texto": ha_quanto(inicio, agora),
        }
    except Exception:
        logger.exception("Idade da fila de opiniões indisponível")
        return _idade_vazia()
