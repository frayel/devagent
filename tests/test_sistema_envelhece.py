"""As atenções que não pioram com o tempo declaram `envelhece=False`.

Sem o campo, `devagent/saude.py` promove a Atenção aberta há mais de 24 h a
Problema e a sessão é mandada corrigir uma lentidão ou uma lacuna histórica
antes de tudo (contrato em devagent/saude.py, ADR 016).
"""

from datetime import datetime, timezone
from typing import Any

from app.services.sistema import (
    ATENCAO,
    Item,
    _grupo,
    resumo_geral,
    verificar_historico_pregoes,
    verificar_issues,
    verificar_tempo_coleta,
)


def test_item_envelhece_por_padrao() -> None:
    assert Item("x", ATENCAO, "y").envelhece is True


def test_coleta_lenta_nao_envelhece() -> None:
    item = verificar_tempo_coleta({"a": 400.0, "b": 300.0})
    assert item.nivel == ATENCAO
    assert item.envelhece is False


def test_issues_que_pedem_acao_nao_envelhecem() -> None:
    github: dict[str, Any] = {
        "issues": [{"numero": 1, "titulo": "t", "labels": ["prioridade"]}]
    }
    item = verificar_issues(github, datetime(2026, 11, 14, tzinfo=timezone.utc))
    assert item.nivel == ATENCAO
    assert item.envelhece is False


def test_lacuna_no_historico_nao_envelhece() -> None:
    agora = datetime(2026, 11, 14, 15, tzinfo=timezone.utc)
    item = verificar_historico_pregoes(["2026-10-01"], agora)
    assert item.nivel == ATENCAO
    assert item.envelhece is False


def test_campo_chega_aos_pendentes_da_pagina() -> None:
    grupo = _grupo("Coleta", [verificar_tempo_coleta({"a": 700.0})])
    assert resumo_geral([grupo])["pendentes"][0]["envelhece"] is False
