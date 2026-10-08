"""O laço do vigia: persona por hora, destravar a cada volta, erros não param."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from devagent.adaptadores import jules


class Relogio:
    def __init__(self, inicio: datetime) -> None:
        self.agora = inicio

    def now(self, tz: Any = None) -> datetime:
        return self.agora

    def sleep(self, segundos: float) -> None:
        self.agora += timedelta(seconds=segundos)


@pytest.fixture
def relogio(monkeypatch: pytest.MonkeyPatch) -> Relogio:
    r = Relogio(datetime(2026, 10, 1, 5, 40, tzinfo=timezone.utc))

    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:  # type: ignore[override]
            return r.agora

    monkeypatch.setattr(jules, "datetime", FakeDatetime)
    monkeypatch.setattr(jules.time, "sleep", r.sleep)
    return r


def _registrar(monkeypatch: pytest.MonkeyPatch, relogio: Relogio, sessoes: list[Any]):
    chamadas: list[tuple[str, Any]] = []

    def iniciar(persona: str, dry_run: bool) -> int:
        chamadas.append(("iniciar", (relogio.agora.strftime("%H:%M"), persona)))
        return 0

    def destravar(espera: int) -> int:
        chamadas.append(("destravar", relogio.agora.strftime("%H:%M")))
        return 0

    monkeypatch.setattr(jules, "iniciar", iniciar)
    monkeypatch.setattr(jules, "destravar", destravar)
    monkeypatch.setattr(jules, "sessoes_do_repo", lambda: sessoes)
    return chamadas


def test_persona_por_hora_e_destravar_a_cada_volta(monkeypatch, relogio):
    chamadas = _registrar(monkeypatch, relogio, [])
    assert jules.vigiar(duracao_minutos=90, intervalo_minutos=5, espera_minutos=5) == 0
    iniciados = [c[1] for c in chamadas if c[0] == "iniciar"]
    assert iniciados == [
        ("05:40", "desenvolvedor"),
        ("06:00", "seguranca"),
        ("07:00", "desenvolvedor"),
    ]
    destravados = [c[1] for c in chamadas if c[0] == "destravar"]
    assert len(destravados) == 18  # 90 min / 5 min
    assert relogio.agora == datetime(2026, 10, 1, 7, 10, tzinfo=timezone.utc)


def test_nao_reinicia_a_hora_que_o_vigia_anterior_ja_iniciou(monkeypatch, relogio):
    titulo = jules.PERSONAS["desenvolvedor"]["titulo"]
    sessoes = [{"title": titulo, "createTime": "2026-10-01T05:01:00Z"}]
    chamadas = _registrar(monkeypatch, relogio, sessoes)
    jules.vigiar(duracao_minutos=30, intervalo_minutos=5, espera_minutos=5)
    iniciados = [c[1] for c in chamadas if c[0] == "iniciar"]
    assert iniciados == [("06:00", "seguranca")]


def test_erro_numa_volta_nao_encerra_o_laco(monkeypatch, relogio):
    chamadas = _registrar(monkeypatch, relogio, [])
    falhas = {"n": 0}

    def destravar_instavel(espera: int) -> int:
        falhas["n"] += 1
        if falhas["n"] == 1:
            raise OSError("rede caiu")
        chamadas.append(("destravar", relogio.agora.strftime("%H:%M")))
        return 0

    monkeypatch.setattr(jules, "destravar", destravar_instavel)
    jules.vigiar(duracao_minutos=15, intervalo_minutos=5, espera_minutos=5)
    assert falhas["n"] == 3
    assert [c for c in chamadas if c[0] == "destravar"] == [
        ("destravar", "05:45"),
        ("destravar", "05:50"),
    ]


def test_rodada_inicia_persona_da_hora_destrava_e_sai(monkeypatch, relogio):
    relogio.agora = datetime(2026, 10, 1, 6, 17, tzinfo=timezone.utc)
    chamadas = _registrar(monkeypatch, relogio, [])
    assert jules.rodada(espera_minutos=5) == 0
    assert chamadas == [("iniciar", ("06:17", "seguranca")), ("destravar", "06:17")]


def test_rodada_nao_repete_persona_ja_iniciada_na_hora(monkeypatch, relogio):
    relogio.agora = datetime(2026, 10, 1, 7, 47, tzinfo=timezone.utc)
    sessao = {
        "title": jules.PERSONAS["desenvolvedor"]["titulo"],
        "createTime": "2026-10-01T07:17:05Z",
        "state": "COMPLETED",
    }
    chamadas = _registrar(monkeypatch, relogio, [sessao])
    assert jules.rodada(espera_minutos=5) == 0
    assert chamadas == [("destravar", "07:47")]
