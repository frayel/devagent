"""ADR 025: a esteira não para e não gasta cota à toa.

Casos de 28/10: o #586 e o #565 (verificação sem achado novo) seguraram a
raia de verificação ~4 h cada um; sessões do desenvolvedor sem spec revisada
nem issue chegavam ao Passo 7 e encerravam sem PR.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from devagent import guardiao_prs
from devagent.adaptadores import jules

# --- Guardião: verificação sem achado fecha na hora ------------------------

VERIFICACAO = {
    "number": 586,
    "title": "verificação: 2026-10-28 · 0 achados",
    "headRefName": "verificacao-1",
    "body": "",
    "url": "u",
}


def test_verificacao_sem_achado_novo() -> None:
    assert guardiao_prs.sem_achado_de_verificacao(VERIFICACAO, [])


def test_verificacao_com_achado_novo_segue() -> None:
    novos = ["docs/verificacao/achados/2026-10-29-x.md"]
    assert not guardiao_prs.sem_achado_de_verificacao(VERIFICACAO, novos)


def test_verificacao_sem_leitura_dos_arquivos_nao_fecha() -> None:
    assert not guardiao_prs.sem_achado_de_verificacao(VERIFICACAO, None)


def test_outra_raia_nao_e_verificacao_sem_achado() -> None:
    pr = {"title": "feat: spec 124", "body": ""}
    assert not guardiao_prs.sem_achado_de_verificacao(pr, [])


def test_ci_falhou_de_verificacao_sem_achado_fecha_sem_issue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chamadas: list[Any] = []
    monkeypatch.setattr(guardiao_prs, "prs_do_agente", lambda: [VERIFICACAO])
    monkeypatch.setattr(
        guardiao_prs,
        "arquivos_do_pr",
        lambda n: ["docs/verificacao/diario.md", "docs/verificacao/achados/velho.md"],
    )
    monkeypatch.setattr(guardiao_prs, "achados_novos_do_pr", lambda n: [])
    monkeypatch.setattr(guardiao_prs, "sh", lambda *a, **k: chamadas.append(a) or "log")
    monkeypatch.setattr(
        guardiao_prs, "comentar", lambda n, c: chamadas.append(("comentar", n, c))
    )

    def fechar(*a: Any, **k: Any) -> None:
        raise AssertionError("não deveria abrir tentativa-falhou")

    monkeypatch.setattr(guardiao_prs, "fechar", fechar)
    guardiao_prs.ci_falhou("verificacao-1", "1")
    comentarios = [c for c in chamadas if c[0] == "comentar"]
    assert comentarios and "ADR 025" in comentarios[0][2]
    assert "@jules" not in comentarios[0][2]
    assert any(a[:3] == ("gh", "pr", "close") for a in chamadas)


# --- Rodada: o desenvolvedor só começa com trabalho -----------------------


@pytest.fixture
def fila(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
    """Repositório falso: backlog, specs e issues controlados pelo teste."""
    estado: dict[str, Any] = {"issues": [], "fila": [], "correcoes": ""}
    (tmp_path / "docs").mkdir()
    monkeypatch.chdir(tmp_path)

    def backlog() -> None:
        (tmp_path / "docs" / "BACKLOG.md").write_text(
            f"# Backlog\n\n## Correções\n\n{estado['correcoes']}\n\n## Features\n",
            encoding="utf-8",
        )

    estado["escrever_backlog"] = backlog
    backlog()
    monkeypatch.setattr(jules, "issues_abertas", lambda: estado["issues"])
    monkeypatch.setattr(jules, "specs_prontas", lambda: estado["fila"])
    monkeypatch.setattr(jules, "fila_do_desenvolvimento", lambda prontas: prontas)
    return estado


def _issue(numero: int, *labels: str, corpo: str = "") -> dict[str, Any]:
    return {
        "numero": numero,
        "titulo": f"issue {numero}",
        "labels": list(labels),
        "corpo": corpo,
    }


def test_sem_nada_nao_ha_trabalho(fila: dict[str, Any]) -> None:
    assert jules.trabalho_do_desenvolvedor("livre") == ""


def test_pr_travado_e_trabalho(fila: dict[str, Any]) -> None:
    assert "travado" in jules.trabalho_do_desenvolvedor("travado")


def test_issue_de_bug_e_trabalho(fila: dict[str, Any]) -> None:
    fila["issues"] = [_issue(557, "bug", "verificacao")]
    assert "#557" in jules.trabalho_do_desenvolvedor("livre")


def test_issues_fora_do_desenvolvimento_nao_contam(fila: dict[str, Any]) -> None:
    fila["issues"] = [
        _issue(1, "tentativa-falhou"),
        _issue(2, "bug", "bloqueado"),
        _issue(3, "enhancement"),
    ]
    assert jules.trabalho_do_desenvolvedor("livre") == ""


def test_correcao_no_backlog_e_trabalho(fila: dict[str, Any]) -> None:
    fila["correcoes"] = "- Corrigir o coletor X."
    fila["escrever_backlog"]()
    assert "backlog" in jules.trabalho_do_desenvolvedor("livre")


def test_spec_revisada_e_trabalho(fila: dict[str, Any]) -> None:
    fila["fila"] = [Path("docs/specs/124-seletor.md")]
    assert "124" in jules.trabalho_do_desenvolvedor("livre")


def test_spec_com_tentativa_fechada_nao_e_trabalho(fila: dict[str, Any]) -> None:
    fila["fila"] = [Path("docs/specs/124-seletor.md")]
    fila["issues"] = [_issue(9, "tentativa-falhou", corpo="spec 124")]
    assert jules.trabalho_do_desenvolvedor("livre") == ""


def test_github_ilegivel_comeca_a_sessao(
    fila: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def falha() -> list[Any]:
        raise OSError("rede caiu")

    monkeypatch.setattr(jules, "issues_abertas", falha)
    assert jules.trabalho_do_desenvolvedor("livre") != ""


def _rodada_sem_trabalho(monkeypatch: pytest.MonkeyPatch, agora: datetime) -> list[str]:
    iniciados: list[str] = []
    monkeypatch.setattr(jules, "tratar_falhas", lambda s, a: False)
    monkeypatch.setattr(jules, "situacao_dos_prs", lambda *a: ("livre", ""))
    monkeypatch.setattr(jules, "trabalho_do_desenvolvedor", lambda situacao: "")
    monkeypatch.setattr(jules, "iniciar", lambda p, dry_run: iniciados.append(p) or 0)
    monkeypatch.delenv("JULES_LIMITE_DIARIO", raising=False)
    monkeypatch.delenv("JULES_INTERVALO_MINUTOS", raising=False)
    jules.rodada_do_desenvolvimento([], agora)
    return iniciados


def test_rodada_sem_trabalho_nao_inicia_o_desenvolvedor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agora = datetime(2026, 10, 29, 4, 0, tzinfo=timezone.utc)
    assert _rodada_sem_trabalho(monkeypatch, agora) == []


def test_especialista_da_hora_roda_mesmo_sem_trabalho_na_fila(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agora = datetime(2026, 10, 29, 6, 5, tzinfo=timezone.utc)
    assert _rodada_sem_trabalho(monkeypatch, agora) == ["seguranca"]
