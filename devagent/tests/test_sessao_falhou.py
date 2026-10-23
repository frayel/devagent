"""Sessão que termina em FAILED é retomada e, se não voltar, ensina (ADR 019).

Casos de 21 e 22/10: as sessões das specs 074 e 076a pararam numa pergunta e
o Jules encerrou a tarefa na mesma mensagem. A resposta nunca chegava, e a
rodada seguinte abria outra sessão do zero.
"""

from __future__ import annotations

import urllib.error
from datetime import datetime, timezone
from typing import Any

import pytest

from devagent.adaptadores import jules

AGORA = datetime(2026, 10, 22, 19, 40, tzinfo=timezone.utc)
PERGUNTA = (
    "Removi as tabelas e os testes que consultam as tabelas antigas falham. "
    "Posso reescrever os testes para usar get_latest_*?"
)


def _falhou(persona: str = "desenvolvedor", atualizada: str = "2026-10-22T19:27:00Z"):
    return {
        "name": "sessions/174",
        "title": jules.PERSONAS[persona]["titulo"],
        "state": "FAILED",
        "createTime": "2026-10-22T18:50:00Z",
        "updateTime": atualizada,
        "prompt": "A fila tem 7 spec(s); a próxima é docs/specs/076a-banco-lote-3.md.",
    }


def _atividades(retomada_em: str | None = None) -> list[dict[str, Any]]:
    acts: list[dict[str, Any]] = [
        {
            "createTime": "2026-10-22T19:26:00Z",
            "agentMessaged": {"agentMessage": PERGUNTA},
        },
        {
            "createTime": "2026-10-22T19:27:00Z",
            "sessionFailed": {"reason": "sem resposta"},
        },
    ]
    if retomada_em:
        acts.append(
            {
                "createTime": retomada_em,
                "userMessaged": {"userMessage": jules.RETOMADA_DE_FALHA},
            }
        )
    return acts


@pytest.fixture
def jules_falso(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    estado: dict[str, Any] = {"enviadas": [], "issues": [], "acts": _atividades()}

    def chamar(metodo: str, caminho: str, corpo: dict[str, Any] | None = None) -> Any:
        if caminho.endswith(":sendMessage"):
            if estado.get("recusar"):
                raise urllib.error.HTTPError(caminho, 400, "x", None, None)  # type: ignore[arg-type]
            estado["enviadas"].append((caminho, corpo))
            return {}
        if "/activities" in caminho:
            return {"activities": estado["acts"]}
        raise AssertionError(caminho)

    monkeypatch.setattr(jules, "chamar", chamar)
    monkeypatch.setattr(jules, "falha_registrada", lambda nome: bool(estado["issues"]))
    monkeypatch.setattr(
        jules,
        "github_post",
        lambda caminho, corpo: estado["issues"].append(corpo) or {"number": 1},
    )
    return estado


def test_primeira_volta_manda_a_retomada_e_segura_a_fila(jules_falso) -> None:
    assert jules.tratar_falhas([_falhou()], AGORA) is True
    assert jules_falso["enviadas"][0][0] == "sessions/174:sendMessage"
    assert jules.MARCA_RETOMADA in jules_falso["enviadas"][0][1]["prompt"]
    assert jules_falso["issues"] == []


def test_retomada_recente_continua_esperando(jules_falso) -> None:
    jules_falso["acts"] = _atividades(retomada_em="2026-10-22T19:30:00Z")
    assert jules.tratar_falhas([_falhou()], AGORA) is True
    assert jules_falso["enviadas"] == []
    assert jules_falso["issues"] == []


def test_retomada_sem_efeito_vira_issue_com_a_fala_do_agente(jules_falso) -> None:
    jules_falso["acts"] = _atividades(retomada_em="2026-10-22T19:00:00Z")
    assert jules.tratar_falhas([_falhou()], AGORA) is False
    issue = jules_falso["issues"][0]
    assert issue["labels"] == [jules.LABEL_TENTATIVA]
    assert "076a" in issue["title"]
    assert "get_latest_*" in issue["body"]
    assert "jules-sessao: sessions/174" in issue["body"]


def test_issue_casa_com_a_spec_na_fila(jules_falso) -> None:
    from pathlib import Path

    from devagent.fila_specs import tentativas_da_spec

    titulo, corpo = jules.corpo_da_falha(_falhou(), _atividades())
    issue = {
        "numero": 7,
        "titulo": titulo,
        "labels": [jules.LABEL_TENTATIVA],
        "corpo": corpo,
    }
    assert tentativas_da_spec(Path("076a-banco-lote-3.md"), [issue]) == [7]


def test_retomada_recusada_registra_na_hora(jules_falso) -> None:
    jules_falso["recusar"] = True
    assert jules.tratar_falhas([_falhou()], AGORA) is False
    assert len(jules_falso["issues"]) == 1


def test_nao_registra_duas_vezes(jules_falso) -> None:
    jules_falso["acts"] = _atividades(retomada_em="2026-10-22T19:00:00Z")
    jules.tratar_falhas([_falhou()], AGORA)
    jules.tratar_falhas([_falhou()], AGORA)
    assert len(jules_falso["issues"]) == 1


def test_especialista_e_retomado_mas_nao_vira_issue(jules_falso) -> None:
    jules_falso["acts"] = _atividades(retomada_em="2026-10-22T19:00:00Z")
    assert jules.tratar_falhas([_falhou("performance")], AGORA) is False
    assert jules_falso["issues"] == []


def test_falha_antiga_e_ignorada(jules_falso) -> None:
    antiga = _falhou(atualizada="2026-10-21T10:00:00Z")
    assert jules.tratar_falhas([antiga], AGORA) is False
    assert jules_falso["enviadas"] == []


def test_sessao_de_fora_do_ciclo_e_ignorada(jules_falso) -> None:
    alheia = {**_falhou(), "title": "Peter Parker – Automated Test Coverage Agent"}
    assert jules.tratar_falhas([alheia], AGORA) is False
    assert jules_falso["enviadas"] == []


def test_pr_vermelho_com_atividade_recente_esta_em_correcao() -> None:
    assert jules.em_correcao({"updated_at": "2026-10-22T19:10:00Z"}, AGORA)
    assert not jules.em_correcao({"updated_at": "2026-10-22T18:00:00Z"}, AGORA)
    assert not jules.em_correcao({}, AGORA)


def test_situacao_espera_pr_vermelho_em_correcao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Agora(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:  # type: ignore[override]
            return AGORA

    monkeypatch.setattr(jules, "datetime", Agora)
    pr = {
        "number": 414,
        "title": "feat: spec 076b",
        "head": {"sha": "abc"},
        "created_at": "2026-10-22T18:55:00Z",
        "updated_at": "2026-10-22T19:05:00Z",
    }
    monkeypatch.setattr(jules, "github_get", lambda caminho: [pr])
    monkeypatch.setattr(jules, "status_ci", lambda repo, sha: "falhou: disciplina")
    situacao, desc = jules.situacao_dos_prs()
    assert situacao == "esperar"
    assert "em correção" in desc
    pr["updated_at"] = "2026-10-22T17:00:00Z"
    assert jules.situacao_dos_prs()[0] == "travado"


def test_rodada_nao_inicia_enquanto_espera_retomada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chamadas: list[str] = []
    monkeypatch.setattr(jules, "sessoes_do_repo", lambda: [])
    monkeypatch.setattr(jules, "tratar_falhas", lambda s, a: True)
    monkeypatch.setattr(jules, "iniciar", lambda p, dry_run: chamadas.append(p) or 0)
    monkeypatch.setattr(jules, "destravar", lambda e: chamadas.append("destravar") or 0)
    jules.rodada(espera_minutos=5)
    assert chamadas == ["destravar"]
