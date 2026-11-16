"""Aceite da spec 163: a coleta do pregão começa de 15 em 15 minutos.

`laco_de_coleta` mede a rodada no relógio monotônico e desconta a duração da
espera (`proxima_espera`), com `PAUSA_MINIMA` de 60 s. Sem rede e sem banco:
`coletar_tudo`, `_relogio`, `intervalo` e `asyncio.sleep` são trocados.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest

from app import agendador
from devagent.aceite import exigir_spec_done


class _Sair(Exception):
    """Interrompe o laço infinito no primeiro sleep."""


def _s(segundos: float) -> timedelta:
    return timedelta(seconds=segundos)


@pytest.mark.parametrize(
    ("intervalo_s", "duracao_s", "esperado_s"),
    [
        (900, 618, 282),
        (900, 840, 60),
        (900, 1000, 60),
        (1800, 618, 1182),
        (7200, 618, 6582),
        (900, 0, 900),
    ],
)
def test_proxima_espera(
    intervalo_s: float, duracao_s: float, esperado_s: float
) -> None:
    exigir_spec_done("163")
    assert agendador.proxima_espera(_s(intervalo_s), _s(duracao_s)) == _s(esperado_s)


def _rodar_laco(
    monkeypatch: pytest.MonkeyPatch, leituras: list[float]
) -> tuple[list[float], list[str]]:
    eventos: list[str] = []
    esperas: list[float] = []
    relogio = iter(leituras)

    def coletar_falso() -> None:
        eventos.append("coleta")

    async def sleep_falso(segundos: float) -> None:
        eventos.append("sleep")
        esperas.append(segundos)
        raise _Sair

    monkeypatch.setattr(agendador, "coletar_tudo", coletar_falso)
    monkeypatch.setattr(agendador, "_relogio", lambda: next(relogio))
    monkeypatch.setattr(agendador, "intervalo", lambda _agora: timedelta(minutes=15))
    monkeypatch.setattr(agendador.asyncio, "sleep", sleep_falso)

    with pytest.raises(_Sair):
        asyncio.run(agendador.laco_de_coleta())
    return esperas, eventos


def test_laco_desconta_a_duracao_da_rodada(monkeypatch: pytest.MonkeyPatch) -> None:
    exigir_spec_done("163")
    esperas, eventos = _rodar_laco(monkeypatch, [0.0, 618.0])
    assert esperas == [282.0]
    assert eventos == ["coleta", "sleep"]


def test_laco_rodada_longa_espera_a_pausa_minima(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exigir_spec_done("163")
    esperas, eventos = _rodar_laco(monkeypatch, [0.0, 1000.0])
    assert esperas == [60.0]
    assert eventos == ["coleta", "sleep"]
