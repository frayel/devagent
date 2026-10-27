"""A fila de specs ready e o prompt do desenvolvedor (ADR 015)."""

from __future__ import annotations

from pathlib import Path

import pytest

from devagent import fila_specs
from devagent.adaptadores import jules


def _spec(pasta: Path, nome: str, status: str) -> None:
    (pasta / nome).write_text(f"---\nid: 1\nstatus: {status}\n---\n", encoding="utf-8")


@pytest.fixture(autouse=True)
def sem_github(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(jules, "issues_de_tentativa", list)
    monkeypatch.setattr(jules, "issues_de_prioridade", list)
    monkeypatch.setattr(jules, "issues_de_producao", list)


@pytest.fixture
def raiz(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    pasta = tmp_path / "docs" / "specs"
    pasta.mkdir(parents=True)
    _spec(pasta, "080-poda.md", "ready")
    _spec(pasta, "068b-regras.md", "ready")
    _spec(pasta, "068a-rota.md", "done")
    _spec(pasta, "069-confianca.md", "ready")
    _spec(pasta, "068-original.md", "draft")
    _spec(pasta, "100-futura.md", "ready")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_ordem_natural_e_so_ready(raiz: Path) -> None:
    nomes = [p.name for p in fila_specs.specs_prontas(raiz)]
    assert nomes == [
        "068b-regras.md",
        "069-confianca.md",
        "080-poda.md",
        "100-futura.md",
    ]


def test_instrucao_aponta_a_menor(raiz: Path) -> None:
    texto = fila_specs.instrucao(fila_specs.specs_prontas(raiz), raiz)
    assert "docs/specs/068b-regras.md" in texto
    assert "não cria, não divide e não edita specs" in texto


def test_fila_vazia_sem_instrucao(tmp_path: Path) -> None:
    assert fila_specs.specs_prontas(tmp_path) == []
    assert fila_specs.instrucao([]) == ""


def test_prompt_do_desenvolvedor_traz_a_proxima_spec(raiz: Path) -> None:
    prompt = jules.prompt_de("desenvolvedor")
    assert prompt.startswith(jules.PERSONAS["desenvolvedor"]["prompt"])
    assert "068b-regras.md" in prompt


def test_prompt_sem_fila_e_o_fixo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert jules.prompt_de("desenvolvedor") == jules.PERSONAS["desenvolvedor"]["prompt"]


def test_auditor_nao_recebe_a_fila(raiz: Path) -> None:
    assert jules.prompt_de("auditor") == jules.PERSONAS["auditor"]["prompt"]


def _tentativa(numero: int, titulo: str, corpo: str = "") -> dict[str, object]:
    return {
        "numero": numero,
        "titulo": titulo,
        "labels": ["tentativa-falhou"],
        "corpo": corpo,
    }


def test_spec_com_tentativa_fechada_fica_para_o_revisor(raiz: Path) -> None:
    issues = [_tentativa(404, "Tentativa fechada: spec 068b perdeu o código")]
    texto = fila_specs.instrucao(fila_specs.specs_prontas(raiz), raiz, issues)
    assert "docs/specs/068b-regras.md" in texto
    assert "#404" in texto
    assert "não a divida" in texto
    assert fila_specs.spec_para_dividir(fila_specs.specs_prontas(raiz), issues)


def test_tentativa_de_outra_spec_nao_desvia(raiz: Path) -> None:
    issues = [
        _tentativa(1, "Tentativa fechada: feat: spec 068 original"),
        _tentativa(2, "Tentativa fechada", "Closes #68b? não: cita #068b"),
        {"numero": 3, "titulo": "spec 068b", "labels": ["outro"]},
    ]
    texto = fila_specs.instrucao(fila_specs.specs_prontas(raiz), raiz, issues)
    assert "não a divida" not in texto
    assert fila_specs.spec_para_dividir(fila_specs.specs_prontas(raiz), issues) is None


def test_tentativa_citada_no_corpo(raiz: Path) -> None:
    issues = [_tentativa(7, "Tentativa fechada: feat: regras", "Implementa a 068b.")]
    assert fila_specs.tentativas_da_spec(fila_specs.specs_prontas(raiz)[0], issues) == [
        7
    ]


def test_divisao_vai_para_o_revisor_nao_para_o_desenvolvedor(
    raiz: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(raiz)
    monkeypatch.setattr(
        jules, "issues_de_tentativa", lambda: [_tentativa(9, "spec 068b falhou")]
    )
    monkeypatch.setattr(jules, "issues_de_prioridade", list)
    dev = jules.prompt_de("desenvolvedor")
    assert "não a divida" in dev
    assert "use o número" not in dev
    revisor = jules.prompt_de("revisor")
    assert "dividir docs/specs/068b-regras.md" in revisor
    assert "Closes #9" in revisor


# ADR 020: issue `prioridade` passa na frente da fila (caso #418).
def _prioridade(numero: int, *labels: str) -> dict[str, object]:
    return {
        "numero": numero,
        "titulo": "[auditoria] data incompleta",
        "labels": ["auditoria", "bug", "prioridade", *labels],
    }


def test_prioridade_vem_antes_da_spec(raiz: Path) -> None:
    issues = [_prioridade(420), _prioridade(418)]
    texto = fila_specs.instrucao(fila_specs.specs_prontas(raiz), raiz, issues)
    assert "#418" in texto and "#420" not in texto
    assert "Closes #418" in texto
    assert "Não implemente spec" in texto


def test_prioridade_bloqueada_nao_desvia(raiz: Path) -> None:
    issues = [_prioridade(418, "bloqueado")]
    texto = fila_specs.instrucao(fila_specs.specs_prontas(raiz), raiz, issues)
    assert "068b-regras.md" in texto
    assert "#418" not in texto


def test_prioridade_com_fila_vazia(tmp_path: Path) -> None:
    texto = fila_specs.instrucao([], tmp_path, [_prioridade(418)])
    assert "Closes #418" in texto


def test_prompt_do_desenvolvedor_traz_a_prioridade(
    raiz: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(jules, "issues_de_prioridade", lambda: [_prioridade(418)])
    assert "Closes #418" in jules.prompt_de("desenvolvedor")


# ADR 024: issue de produção aberta vai na frente, com número.
def test_issue_de_producao_vai_na_frente(raiz: Path) -> None:
    issues = [
        {
            "numero": 534,
            "titulo": "Produção incorreta",
            "labels": ["producao-incorreta"],
        },
        {"numero": 9, "titulo": "x", "labels": ["sistema-com-problema", "bloqueado"]},
    ]
    texto = fila_specs.instrucao(fila_specs.specs_prontas(raiz), raiz, issues)
    assert texto.startswith("Há issues de produção abertas (#534)")
    assert "#9" not in texto
    assert "docs/specs/068b-regras.md" in texto
