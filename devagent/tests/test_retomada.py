"""Retomada depois de ambiente reiniciado (ADR 009): vigia e guardião."""

from __future__ import annotations

from typing import Any

import pytest

from devagent import guardiao_prs
from devagent.adaptadores import jules

URL = "https://github.com/dono/repo/pull/42"


def sessao(
    pr: str | None = URL, estado: str = "AWAITING_USER_FEEDBACK"
) -> dict[str, Any]:
    s: dict[str, Any] = {
        "name": "sessions/123",
        "title": "Desenvolvedor · ciclo",
        "state": estado,
        "updateTime": "2026-01-01T00:00:00Z",
    }
    if pr:
        s["outputs"] = [{"pullRequest": {"url": pr, "title": "feat: x"}}]
    return s


@pytest.fixture
def chamadas(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, Any]]:
    registro: list[tuple[str, str, Any]] = []

    def chamar(metodo: str, caminho: str, corpo: Any = None) -> Any:
        registro.append((metodo, caminho, corpo))
        return {}

    monkeypatch.setattr(jules, "chamar", chamar)
    return registro


def test_sessao_sem_pr_recebe_a_resposta_padrao() -> None:
    assert jules.resposta_para(sessao(pr=None)) == ("responder", jules.RESPOSTA_PADRAO)


def test_pr_aberto_aponta_a_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        jules,
        "estado_do_pr",
        lambda url: {"aberto": True, "mesclado": False, "branch": "feat/026-x"},
    )
    acao, texto = jules.resposta_para(sessao())
    assert acao == "responder"
    assert "git checkout -B feat/026-x origin/feat/026-x" in texto
    assert "Não recomece da `main`" in texto
    assert URL in texto


@pytest.mark.parametrize("mesclado", [True, False])
def test_pr_fechado_encerra(monkeypatch: pytest.MonkeyPatch, mesclado: bool) -> None:
    monkeypatch.setattr(
        jules,
        "estado_do_pr",
        lambda url: {"aberto": False, "mesclado": mesclado, "branch": "b"},
    )
    acao, motivo = jules.resposta_para(sessao())
    assert acao == "encerrar"
    assert URL in motivo


def test_pr_ilegivel_cai_na_resposta_padrao(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(jules, "estado_do_pr", lambda url: None)
    assert jules.resposta_para(sessao())[0] == "responder"


def test_destravar_encerra_sessao_de_pr_fechado(
    monkeypatch: pytest.MonkeyPatch, chamadas: list[tuple[str, str, Any]]
) -> None:
    monkeypatch.setattr(jules, "sessoes_do_repo", lambda: [sessao()])
    monkeypatch.setattr(
        jules,
        "estado_do_pr",
        lambda url: {"aberto": False, "mesclado": False, "branch": "b"},
    )
    jules.destravar(espera_minutos=5)
    metodos = [(m, c) for m, c, _ in chamadas]
    assert ("POST", "sessions/123:sendMessage") in metodos
    assert ("DELETE", "sessions/123") in metodos
    texto = chamadas[0][2]["prompt"]
    assert texto.startswith("Encerre esta tarefa")


@pytest.mark.parametrize(
    "alvo",
    [
        "10534620312189957875",
        "sessions/10534620312189957875",
        "https://jules.google.com/task/10534620312189957875",
        "https://jules.google.com/task/10534620312189957875/",
    ],
)
def test_nome_da_sessao_aceita_id_e_url(alvo: str) -> None:
    assert jules.nome_da_sessao(alvo) == "sessions/10534620312189957875"


def test_encerrar_segue_se_delete_nao_existir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import urllib.error

    enviados: list[str] = []

    def chamar(metodo: str, caminho: str, corpo: Any = None) -> Any:
        enviados.append(metodo)
        if metodo == "DELETE":
            raise urllib.error.HTTPError(caminho, 404, "não", None, None)  # type: ignore[arg-type]
        return {}

    monkeypatch.setattr(jules, "chamar", chamar)
    assert jules.encerrar("123") == 0
    assert enviados == ["POST", "DELETE"]


def test_cobranca_do_guardiao_traz_a_retomada(monkeypatch: pytest.MonkeyPatch) -> None:
    pr = {"number": 7, "headRefName": "feat/026-x", "url": "u", "title": "t"}
    comentarios: list[str] = []
    monkeypatch.setattr(guardiao_prs, "prs_do_agente", lambda: [pr])
    monkeypatch.setattr(guardiao_prs, "comentarios", lambda n: [])
    monkeypatch.setattr(guardiao_prs, "sh", lambda *a, **k: "log")
    monkeypatch.setattr(
        guardiao_prs, "comentar", lambda n, corpo: comentarios.append(corpo)
    )
    guardiao_prs.ci_falhou("feat/026-x", "1")
    assert comentarios
    assert "git checkout -B feat/026-x origin/feat/026-x" in comentarios[0]
    assert "não recomece" in comentarios[0]
