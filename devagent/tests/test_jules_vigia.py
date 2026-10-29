"""O laço do vigia e a rodada: quem começa, quando espera, erros não param."""

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


def _rodada(monkeypatch, relogio, sessoes, prs=("livre", "")):
    chamadas = _registrar(monkeypatch, relogio, sessoes)
    monkeypatch.setattr(jules, "situacao_dos_prs", lambda *a: prs)
    # As raias paralelas têm testes próprios (test_raias.py).
    monkeypatch.setattr(jules, "rodada_das_raias", lambda s, a: None)
    monkeypatch.delenv("JULES_LIMITE_DIARIO", raising=False)
    monkeypatch.delenv("JULES_INTERVALO_MINUTOS", raising=False)
    return chamadas


def _sessao(persona: str, criada: str, estado: str = "COMPLETED") -> dict[str, Any]:
    return {
        "title": jules.PERSONAS[persona]["titulo"],
        "createTime": criada,
        "state": estado,
    }


def test_rodada_inicia_persona_da_hora_destrava_e_sai(monkeypatch, relogio):
    relogio.agora = datetime(2026, 10, 1, 6, 17, tzinfo=timezone.utc)
    chamadas = _rodada(monkeypatch, relogio, [])
    assert jules.rodada(espera_minutos=5) == 0
    assert chamadas == [("iniciar", ("06:17", "seguranca")), ("destravar", "06:17")]


def test_rodada_segue_na_mesma_hora_quando_a_sessao_acabou(monkeypatch, relogio):
    # Antes, uma sessão por hora: a que terminava em 10 min sem nada a fazer
    # deixava o agente parado 50 min. Agora a próxima começa na volta seguinte.
    relogio.agora = datetime(2026, 10, 1, 5, 22, tzinfo=timezone.utc)
    sessoes = [_sessao("desenvolvedor", "2026-10-01T05:05:00Z")]
    chamadas = _rodada(monkeypatch, relogio, sessoes)
    jules.rodada(espera_minutos=5)
    assert chamadas[0] == ("iniciar", ("05:22", "desenvolvedor"))


def test_especialista_que_perdeu_a_hora_entra_depois(monkeypatch, relogio):
    relogio.agora = datetime(2026, 10, 1, 8, 40, tzinfo=timezone.utc)
    sessoes = [_sessao("desenvolvedor", "2026-10-01T05:50:00Z")]
    chamadas = _rodada(monkeypatch, relogio, sessoes)
    jules.rodada(espera_minutos=5)
    assert chamadas[0] == ("iniciar", ("08:40", "seguranca"))


def test_especialista_que_ja_rodou_hoje_nao_repete(monkeypatch, relogio):
    relogio.agora = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)
    sessoes = [_sessao("seguranca", "2026-10-01T06:01:00Z")]
    chamadas = _rodada(monkeypatch, relogio, sessoes)
    jules.rodada(espera_minutos=5)
    assert chamadas[0] == ("iniciar", ("09:00", "desenvolvedor"))


def test_pr_esperando_merge_segura_a_proxima_sessao(monkeypatch, relogio):
    chamadas = _rodada(monkeypatch, relogio, [], prs=("esperar", "PR #9 (rodando)"))
    jules.rodada(espera_minutos=5)
    assert chamadas == [("destravar", "05:40")]


def test_pr_travado_chama_o_desenvolvedor_e_nao_o_especialista(monkeypatch, relogio):
    relogio.agora = datetime(2026, 10, 1, 6, 5, tzinfo=timezone.utc)
    chamadas = _rodada(
        monkeypatch, relogio, [], prs=("travado", "PR #9 (falhou: test)")
    )
    jules.rodada(espera_minutos=5)
    assert chamadas[0] == ("iniciar", ("06:05", "desenvolvedor"))


def test_ritmo_da_cota_espalha_o_desenvolvedor(monkeypatch, relogio):
    sessoes = [
        _sessao("desenvolvedor", "2026-10-01T05:00:00Z"),
        _sessao("seguranca", "2026-10-01T06:00:00Z"),
    ]
    chamadas = _rodada(monkeypatch, relogio, sessoes)
    # Limite 15, reserva 4, 2 já usadas: restam 9 vagas até a sessão das 05:00
    # sair da janela (05:00 do dia seguinte). A conta se refaz a cada volta:
    # a espera vence quando 9 × (t − 05:00) = 29:00 − t, às 07:24 (ADR 028).
    monkeypatch.setenv("JULES_LIMITE_DIARIO", "15")
    jules.rodada(espera_minutos=5)
    assert chamadas == [("destravar", "05:40")]
    relogio.agora = datetime(2026, 10, 1, 7, 20, tzinfo=timezone.utc)
    jules.rodada(espera_minutos=5)
    assert ("iniciar", ("07:20", "desenvolvedor")) not in chamadas
    relogio.agora = datetime(2026, 10, 1, 7, 30, tzinfo=timezone.utc)
    jules.rodada(espera_minutos=5)
    assert ("iniciar", ("07:30", "desenvolvedor")) in chamadas


def test_ritmo_conta_as_sessoes_das_raias(monkeypatch):
    # ADR 028: as raias gastam da mesma cota; o desenvolvedor espaça mais.
    monkeypatch.setenv("JULES_LIMITE_DIARIO", "100")
    monkeypatch.delenv("JULES_INTERVALO_MINUTOS", raising=False)
    agora = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)
    so_dev = [_sessao("desenvolvedor", "2026-10-29T00:00:00Z")]
    raias = so_dev + [
        _sessao("verificador", f"2026-10-29T{h:02d}:00:00Z") for h in range(1, 12)
    ]
    # 12 h até a sessão das 00:00 sair: 95 vagas contra 84.
    assert jules.intervalo_do_desenvolvedor(so_dev, agora) == timedelta(hours=12) / 95
    assert jules.intervalo_do_desenvolvedor(raias, agora) == timedelta(hours=12) / 84


def test_ritmo_sem_vaga_espera_a_proxima(monkeypatch):
    monkeypatch.setenv("JULES_LIMITE_DIARIO", "6")  # 2 vagas além da reserva
    monkeypatch.delenv("JULES_INTERVALO_MINUTOS", raising=False)
    agora = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)
    sessoes = [
        _sessao("desenvolvedor", "2026-10-29T02:00:00Z"),
        _sessao("revisor", "2026-10-29T03:00:00Z"),
    ]
    assert jules.intervalo_do_desenvolvedor(sessoes, agora) == timedelta(hours=14)


def test_ritmo_sem_historico_nao_espera(monkeypatch):
    monkeypatch.setenv("JULES_LIMITE_DIARIO", "100")
    monkeypatch.delenv("JULES_INTERVALO_MINUTOS", raising=False)
    agora = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)
    assert jules.intervalo_do_desenvolvedor([], agora) == timedelta(0)


def test_intervalo_fixo_tem_precedencia(monkeypatch):
    monkeypatch.setenv("JULES_LIMITE_DIARIO", "100")
    monkeypatch.setenv("JULES_INTERVALO_MINUTOS", "0")
    assert jules.intervalo_do_desenvolvedor() == timedelta(0)
    monkeypatch.delenv("JULES_INTERVALO_MINUTOS")
    assert jules.intervalo_do_desenvolvedor() == timedelta(minutes=15)


def test_erro_na_rodada_ainda_destrava(monkeypatch, relogio):
    chamadas = _rodada(monkeypatch, relogio, [])

    def falha():
        raise OSError("github fora")

    monkeypatch.setattr(jules, "situacao_dos_prs", falha)
    jules.rodada(espera_minutos=5)
    assert chamadas == [("destravar", "05:40")]


def _zumbi(estado: str, atualizada: str, pr: str | None = None) -> dict[str, Any]:
    s: dict[str, Any] = {
        "name": "sessions/1",
        "title": jules.PERSONAS["seguranca"]["titulo"],
        "state": estado,
        "createTime": "2026-10-18T06:17:00Z",
        "updateTime": atualizada,
    }
    if pr:
        s["outputs"] = [{"pullRequest": {"url": pr}}]
    return s


AGORA_18 = datetime(2026, 10, 18, 7, 47, tzinfo=timezone.utc)
PR_335 = "https://github.com/frayel/devagent/pull/335"


def test_sessao_com_pr_mesclado_e_zumbi(monkeypatch):
    # O caso de 18/10: Sentinel "ativo" depois do merge do #335.
    monkeypatch.setattr(
        jules,
        "estado_do_pr",
        lambda url: {"aberto": False, "mesclado": True, "branch": "b"},
    )
    s = _zumbi("IN_PROGRESS", "2026-10-18T07:30:00Z", PR_335)
    assert "mesclado" in jules.motivo_de_zumbi(s, AGORA_18)


def test_sessao_com_pr_aberto_e_recente_nao_e_zumbi(monkeypatch):
    monkeypatch.setattr(
        jules,
        "estado_do_pr",
        lambda url: {"aberto": True, "mesclado": False, "branch": "b"},
    )
    s = _zumbi("IN_PROGRESS", "2026-10-18T07:30:00Z", PR_335)
    assert jules.motivo_de_zumbi(s, AGORA_18) == ""


def test_sessao_parada_ha_tres_horas_e_zumbi():
    s = _zumbi("PAUSED", "2026-10-18T04:40:00Z")
    assert "3.1 h" in jules.motivo_de_zumbi(s, AGORA_18)


def test_sessao_concluida_nunca_e_zumbi():
    s = _zumbi("COMPLETED", "2026-10-17T00:00:00Z")
    assert jules.motivo_de_zumbi(s, AGORA_18) == ""


def test_rodada_encerra_zumbi_e_segue_com_a_fila(monkeypatch, relogio):
    relogio.agora = AGORA_18
    zumbi = _zumbi("IN_PROGRESS", "2026-10-18T07:30:00Z", PR_335)
    chamadas = _rodada(monkeypatch, relogio, [zumbi])
    monkeypatch.setattr(
        jules,
        "estado_do_pr",
        lambda url: {"aberto": False, "mesclado": True, "branch": "b"},
    )
    encerradas: list[str] = []
    monkeypatch.setattr(
        jules, "encerrar", lambda nome, motivo="": encerradas.append(nome)
    )
    jules.rodada(espera_minutos=5)
    assert encerradas == ["sessions/1"]
    assert chamadas[0] == ("iniciar", ("07:47", "desenvolvedor"))


def test_iniciar_nao_trava_em_zumbi(monkeypatch):
    zumbi = _zumbi("PAUSED", "2026-10-18T00:00:00Z")
    monkeypatch.setattr(jules, "sessoes_do_repo", lambda: [zumbi])
    criadas: list[Any] = []
    monkeypatch.setattr(
        jules, "chamar", lambda m, c, corpo=None: criadas.append(c) or {}
    )
    monkeypatch.delenv("JULES_LIMITE_DIARIO", raising=False)
    jules.iniciar("desenvolvedor", dry_run=False)
    assert criadas == ["sessions"]
