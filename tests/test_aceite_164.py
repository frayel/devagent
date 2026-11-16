"""Aceite da spec 164: a leitura das opiniões corre num laço próprio.

O `consultor_opinioes` sai da rodada de mercado (`_coletar`) e ganha
`rodar_opinioes` e `laco_das_opinioes`, no mesmo ritmo da spec 163. Sem rede e
sem banco: os coletores, a instrumentação, o banco, `_relogio`, `intervalo` e
`asyncio.sleep` são trocados.
"""

from __future__ import annotations

import asyncio
import importlib
import pkgutil
from datetime import timedelta
from typing import Any

import pytest

import app.collectors
from app import agendador
from devagent.aceite import exigir_spec_done


class _Sair(Exception):
    """Interrompe o laço infinito no primeiro sleep."""


def test_coletar_nao_chama_as_opinioes(monkeypatch: pytest.MonkeyPatch) -> None:
    exigir_spec_done("164")
    chamadas: list[str] = []
    gravados: list[dict[str, float]] = []

    for info in pkgutil.iter_modules(app.collectors.__path__):
        modulo = importlib.import_module(f"app.collectors.{info.name}")
        if hasattr(modulo, "collect_and_save"):
            monkeypatch.setattr(modulo, "collect_and_save", lambda: True)
    monkeypatch.setattr(
        "app.collectors.consultor_opinioes.collect_and_save",
        lambda: chamadas.append("opinioes") or True,
    )
    # Sem snapshot no banco: toda janela cai na partida a frio e coleta.
    monkeypatch.setattr("app.banco.ler_snapshot", lambda *_a, **_k: None)
    monkeypatch.setattr("app.banco.gravar_snapshot", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "app.consultor.avaliador_historico.rodar_backtest", lambda: None
    )

    def gravar_falso(tempos: dict[str, float], *_a: Any, **_k: Any) -> None:
        gravados.append(dict(tempos))

    monkeypatch.setattr("app.database.gravar_instrumentacao_rodada", gravar_falso)

    agendador._coletar()

    assert chamadas == []
    assert len(gravados) == 1
    assert "consultor_opinioes" not in gravados[0]
    assert "ibovespa" in gravados[0]


def test_rodar_opinioes_chama_o_coletor(monkeypatch: pytest.MonkeyPatch) -> None:
    exigir_spec_done("164")
    chamadas: list[str] = []
    monkeypatch.setattr(
        "app.collectors.consultor_opinioes.collect_and_save",
        lambda: chamadas.append("opinioes") or True,
    )
    agendador.rodar_opinioes()
    assert chamadas == ["opinioes"]


def test_rodar_opinioes_engole_a_falha_sem_tocar_no_estado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exigir_spec_done("164")

    def quebra() -> bool:
        raise RuntimeError("caiu")

    monkeypatch.setattr("app.collectors.consultor_opinioes.collect_and_save", quebra)
    monkeypatch.setitem(agendador.estado, "ultimo_erro", "erro anterior")
    agendador.rodar_opinioes()
    assert agendador.estado["ultimo_erro"] == "erro anterior"


def _rodar_laco(
    monkeypatch: pytest.MonkeyPatch, leituras: list[float]
) -> tuple[list[float], list[str]]:
    eventos: list[str] = []
    esperas: list[float] = []
    relogio = iter(leituras)

    def rodar_falso() -> None:
        eventos.append("opinioes")

    async def sleep_falso(segundos: float) -> None:
        eventos.append("sleep")
        esperas.append(segundos)
        raise _Sair

    monkeypatch.setattr(agendador, "rodar_opinioes", rodar_falso)
    monkeypatch.setattr(agendador, "_relogio", lambda: next(relogio))
    monkeypatch.setattr(agendador, "intervalo", lambda _agora: timedelta(minutes=15))
    monkeypatch.setattr(agendador.asyncio, "sleep", sleep_falso)

    with pytest.raises(_Sair):
        asyncio.run(agendador.laco_das_opinioes())
    return esperas, eventos


def test_laco_desconta_a_duracao_da_volta(monkeypatch: pytest.MonkeyPatch) -> None:
    exigir_spec_done("164")
    esperas, eventos = _rodar_laco(monkeypatch, [0.0, 246.0])
    assert esperas == [654.0]
    assert eventos == ["opinioes", "sleep"]


def test_laco_volta_longa_espera_a_pausa_minima(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exigir_spec_done("164")
    esperas, _ = _rodar_laco(monkeypatch, [0.0, 1000.0])
    assert esperas == [60.0]
