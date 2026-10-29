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


# ADRs 024 e 026: issue de produção sem correção mesclada é a sessão inteira.
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
    assert texto.startswith(
        "Há issues de produção abertas sem correção mesclada (#534)"
    )
    assert "corrigir a #534" in texto
    assert "Closes #534" in texto
    assert "#9" not in texto
    # A fila não compete com a produção quebrada (#577, 28/10).
    assert "068b-regras.md" not in texto


def test_producao_tira_a_prioridade_do_prompt(raiz: Path) -> None:
    issues = [
        {
            "numero": 577,
            "titulo": "Produção incorreta",
            "labels": ["producao-incorreta"],
        },
        {"numero": 573, "titulo": "Gemini", "labels": ["prioridade"]},
    ]
    texto = fila_specs.instrucao(fila_specs.specs_prontas(raiz), raiz, issues)
    assert "#577" in texto
    assert "#573" not in texto


def test_correcao_mergeada_devolve_a_fila(raiz: Path) -> None:
    issues = [
        {
            "numero": 534,
            "titulo": "Produção incorreta",
            "labels": ["producao-incorreta"],
            "correcao_mergeada": True,
        }
    ]
    texto = fila_specs.instrucao(fila_specs.specs_prontas(raiz), raiz, issues)
    assert texto.startswith("As issues de produção abertas (#534) já têm correção")
    assert "docs/specs/068b-regras.md" in texto


def test_correcao_mergeada_le_os_comentarios() -> None:
    marca = fila_specs.MARCA_CORRECAO
    assert not fila_specs.correcao_mergeada([])
    assert not fila_specs.correcao_mergeada(["<!-- falhas: a -->"])
    assert fila_specs.correcao_mergeada(["<!-- falhas: a -->", f"PR #1 {marca}"])
    # Falha nova depois da correção: volta a ser pendente.
    assert not fila_specs.correcao_mergeada(
        [f"PR #1 {marca}", "**A correção mergeada não resolveu:** ..."]
    )
    assert not fila_specs.correcao_mergeada(
        [f"PR #1 {marca}", "Os problemas mudaram. A descrição foi atualizada."]
    )
    assert fila_specs.correcao_mergeada(
        [f"PR #1 {marca}", "comentário qualquer", f"PR #2 {marca}"]
    )


def test_marcar_correcoes_so_le_issues_de_producao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devagent import estado_github

    lidas: list[str] = []

    def get(caminho: str) -> list[dict[str, str]]:
        lidas.append(caminho)
        return [{"body": f"PR #1 {fila_specs.MARCA_CORRECAO}"}]

    monkeypatch.setattr(estado_github, "_get", get)
    issues = [
        {"numero": 1, "labels": ["producao-incorreta"]},
        {"numero": 2, "labels": ["bug"]},
    ]
    estado_github.marcar_correcoes("dono/repo", issues)
    assert issues[0]["correcao_mergeada"] is True
    assert "correcao_mergeada" not in issues[1]
    assert lidas == ["/repos/dono/repo/issues/1/comments?per_page=100"]
