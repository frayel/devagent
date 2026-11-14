"""Raias paralelas (ADR 021): quem pode escrever onde, e quando cada uma roda."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from devagent import conferir_pr, fila_specs, guardiao_prs, raias
from devagent.auditoria import achados_para_issues
from devagent.conferir_pr import conferir


# --- raia pelo título ------------------------------------------------------


@pytest.mark.parametrize(
    ("titulo", "raia"),
    [
        ("spec: 084 · radar de volume", raias.ESPECIFICACAO),
        ("Spec: 085 · algo", raias.ESPECIFICACAO),
        ("revisão: spec 084 · dividida", raias.REVISAO),
        ("revisao: spec 084", raias.REVISAO),
        ("verificação: 2026-10-23 · 2 achados", raias.VERIFICACAO),
        ("verificacao: 2026-10-23", raias.VERIFICACAO),
        ("auditoria: 2026-10-23 · 0 achados", raias.AUDITORIA),
        ("feat: spec 084", raias.DESENVOLVIMENTO),
        ("docs: spec a partir da issue #12", raias.DESENVOLVIMENTO),
        ("🛡️ Sentinel: escape no rodapé", raias.DESENVOLVIMENTO),
        ("specs: palavra parecida não é prefixo", raias.DESENVOLVIMENTO),
    ],
)
def test_raia_do_titulo(titulo: str, raia: str) -> None:
    assert raias.raia_do_titulo(titulo) == raia


def test_cada_raia_fica_na_sua_faixa() -> None:
    assert raias.fora_da_raia(raias.ESPECIFICACAO, ["docs/specs/084-x.md"]) == []
    assert raias.fora_da_raia(raias.ESPECIFICACAO, ["app/x.py"]) == ["app/x.py"]
    assert raias.fora_da_raia(raias.REVISAO, ["docs/BACKLOG.md"]) == ["docs/BACKLOG.md"]
    assert (
        raias.fora_da_raia(raias.VERIFICACAO, ["docs/verificacao/achados/a.md"]) == []
    )
    assert raias.fora_da_raia(raias.VERIFICACAO, ["docs/specs/084-x.md"]) == [
        "docs/specs/084-x.md"
    ]
    assert (
        raias.fora_da_raia(raias.DESENVOLVIMENTO, ["app/x.py", "docs/specs/a.md"]) == []
    )
    assert raias.fora_da_raia(raias.DESENVOLVIMENTO, ["docs/verificacao/a.md"]) == [
        "docs/verificacao/a.md"
    ]


# --- regra 8 do conferir_pr --------------------------------------------------


def _git(raiz: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=raiz, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "docs/specs").mkdir(parents=True)
    (tmp_path / "docs/specs/001-a.md").write_text("---\nstatus: ready\n---\n")
    (tmp_path / "app").mkdir()
    (tmp_path / "app/x.py").write_text("x = 1\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "base")
    _git(tmp_path, "branch", "base")
    _git(tmp_path, "checkout", "-q", "-b", "trabalho")
    return tmp_path


def test_spec_que_mexe_no_codigo_reprova(repo: Path) -> None:
    (repo / "docs/specs/002-b.md").write_text("---\nstatus: ready\n---\n")
    (repo / "app/x.py").write_text("x = 2\n")
    falhas = conferir(repo, "base", titulo="spec: 002 · b").falhas
    assert any("app/x.py" in f and "especificacao" in f for f in falhas)


def test_spec_na_faixa_passa(repo: Path) -> None:
    (repo / "docs/specs/002-b.md").write_text("---\nstatus: ready\n---\n")
    assert conferir(repo, "base", titulo="spec: 002 · b").falhas == []


def test_desenvolvimento_nao_escreve_achado_do_verificador(repo: Path) -> None:
    (repo / "docs/verificacao").mkdir(parents=True)
    (repo / "docs/verificacao/diario.md").write_text("x\n")
    (repo / "app/x.py").write_text("x = 2\n")
    falhas = conferir(repo, "base", titulo="fix: algo").falhas
    assert any("docs/verificacao/diario.md" in f for f in falhas)


def test_desenvolvimento_nao_cria_spec(repo: Path) -> None:
    (repo / "docs/specs/002-b.md").write_text("---\nstatus: ready\n---\n")
    falhas = conferir(repo, "base", titulo="docs: issue vira spec").falhas
    assert any("002-b.md" in f and "spec nova" in f for f in falhas)


def test_desenvolvimento_nao_divide_spec(repo: Path) -> None:
    (repo / "docs/specs/001-a.md").write_text("---\nstatus: draft\n---\n")
    falhas = conferir(repo, "base", titulo="docs: dividir 001").falhas
    assert any("001-a.md" in f and "draft" in f for f in falhas)


def test_desenvolvimento_marca_done(repo: Path) -> None:
    (repo / "docs/specs/001-a.md").write_text("---\nstatus: done\n---\n")
    falhas = conferir(repo, "base", titulo="feat: spec 001").falhas
    assert not any("ADR 023" in f for f in falhas)


def test_sem_titulo_a_regra_nao_se_aplica(repo: Path) -> None:
    (repo / "app/x.py").write_text("x = 2\n")
    assert conferir(repo, "base", titulo="").falhas == []


# --- fila de specs com revisão -----------------------------------------------


def _spec(pasta: Path, nome: str, status: str, revisada: bool = False) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    extra = "revisada: 2026-10-23\n" if revisada else ""
    caminho = pasta / nome
    caminho.write_text(f"---\nstatus: {status}\n{extra}---\n", encoding="utf-8")
    return caminho


def test_spec_sem_revisao_fica_fora_da_fila_do_desenvolvimento(tmp_path: Path) -> None:
    pasta = tmp_path / "docs/specs"
    antiga = _spec(pasta, "083-antiga.md", "ready")
    revisada = _spec(pasta, "084-revisada.md", "ready", revisada=True)
    crua = _spec(pasta, "085-crua.md", "ready")
    prontas = fila_specs.specs_prontas(tmp_path)
    assert fila_specs.fila_do_desenvolvimento(prontas, "084") == [antiga, revisada]
    assert fila_specs.fila_da_revisao(prontas, "084") == [crua]
    # Sem o corte configurado, nada espera revisão.
    assert fila_specs.fila_da_revisao(prontas, "") == []


def test_instrucao_com_tudo_em_revisao_nao_manda_implementar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(fila_specs, "revisao_desde", lambda: "084")
    crua = _spec(tmp_path / "docs/specs", "084-crua.md", "ready")
    texto = fila_specs.instrucao([crua], tmp_path)
    assert "esperam a raia de revisão" in texto
    assert "Não as implemente" in texto


def test_proximo_numero_conta_subpastas_e_reservas(tmp_path: Path) -> None:
    pasta = tmp_path / "docs/specs"
    _spec(pasta, "083-a.md", "ready")
    _spec(pasta / "done", "090b-b.md", "done")
    assert fila_specs.proximo_numero(tmp_path) == "091"
    assert fila_specs.proximo_numero(tmp_path, {91, 92}) == "093"


# --- quem a rodada abre ----------------------------------------------------------


# --- ADR 023: o desenvolvimento não cria nem edita specs ------------------------

SPEC = "---\nid: 084\nstatus: ready\nrevisada: 2026-10-27\n---\n\n# Título\n"


def test_desenvolvimento_so_pode_marcar_done() -> None:
    feita = SPEC.replace("status: ready", "status: done")
    assert raias.edicao_de_spec_proibida(SPEC, feita) == ""
    assert raias.edicao_de_spec_proibida(SPEC, SPEC) == ""


def test_desenvolvimento_nao_cria_divide_nem_edita_spec() -> None:
    assert raias.edicao_de_spec_proibida(None, SPEC) == "spec nova"
    assert raias.edicao_de_spec_proibida(SPEC, None) == "spec apagada"
    editada = SPEC.replace("# Título", "# Outro título")
    assert raias.edicao_de_spec_proibida(SPEC, editada) == "texto da spec alterado"
    rascunho = SPEC.replace("status: ready", "status: draft")
    assert "draft" in raias.edicao_de_spec_proibida(SPEC, rascunho)


# --- achados do verificador e guardião ------------------------------------------


def test_labels_do_verificador() -> None:
    assert achados_para_issues.labels_do_achado("verificacao", "alta") == [
        "verificacao",
        "bug",
        "prioridade",
    ]
    assert achados_para_issues.labels_do_achado("verificacao", "baixa") == [
        "verificacao",
        "bug",
    ]
    assert achados_para_issues.labels_do_achado("auditoria", "alta")[-1] == (
        "producao-incorreta"
    )


def test_guardiao_fecha_pr_de_raia_sem_tentativa(monkeypatch) -> None:
    comandos: list[tuple[str, ...]] = []
    monkeypatch.setattr(guardiao_prs, "absorvido_pela_main", lambda b: False)
    monkeypatch.setattr(guardiao_prs, "comentar", lambda n, c: None)
    monkeypatch.setattr(guardiao_prs, "sh", lambda *a, **k: comandos.append(a) or "")
    pr = {"number": 7, "title": "spec: 084 · x", "headRefName": "b", "url": "u"}
    guardiao_prs.fechar(pr, "conflito grande")
    assert ("gh", "pr", "close", "7", "--delete-branch") in comandos
    assert not any("issue" in c for c in comandos)


def test_revisao_so_cria_partes_da_spec_alterada() -> None:
    assert raias.spec_nova_fora_do_alvo(
        ["docs/specs/093a-x.md", "docs/specs/122-y.md"], ["docs/specs/093-x.md"]
    ) == ["docs/specs/122-y.md"]
    assert (
        raias.spec_nova_fora_do_alvo(
            ["docs/specs/092aa-x.md"], ["docs/specs/092a-x.md"]
        )
        == []
    )


def test_raia_declarada_no_corpo() -> None:
    assert (
        raias.raia_declarada("<!-- devagent:raia:especificacao -->") == "especificacao"
    )
    assert raias.raia_declarada("<!-- devagent:raia:revisão -->") == "revisao"
    assert (
        raias.raia_declarada("<!-- devagent:raia:desenvolvimento -->")
        == "desenvolvimento"
    )
    assert raias.raia_declarada("corpo sem marcador") is None


def test_conferir_raia_declarada_no_corpo(monkeypatch: pytest.MonkeyPatch) -> None:
    res = conferir_pr.Resultado()
    monkeypatch.setattr(
        conferir_pr,
        "corpo_do_pr",
        lambda: "<!-- devagent:raia:especificacao -->\ncorpo",
    )
    conferir_pr.conferir_raia_declarada(res, "desenvolvimento")
    assert res.falhas and "declara a raia `especificacao`" in res.falhas[0]

    res_ok = conferir_pr.Resultado()
    conferir_pr.conferir_raia_declarada(res_ok, "especificacao")
    assert res_ok.falhas == []


def test_verificacao_sem_achado_reprova(repo: Path) -> None:
    (repo / "docs/verificacao/relatorios").mkdir(parents=True)
    (repo / "docs/verificacao/relatorios/r.md").write_text("ok\n")
    falhas = conferir(
        repo, "base", True, titulo="verificação: 0 achados", corpo=""
    ).falhas
    assert any("sem achado" in f for f in falhas)


def test_revisao_exige_conferencia_no_corpo(repo: Path) -> None:
    (repo / "docs/specs/001-a.md").write_text("---\nstatus: ready\nrevisada: x\n---\n")
    falhas = conferir(repo, "base", True, titulo="revisão: 001", corpo="ok").falhas
    assert any("Tamanho:" in f for f in falhas)
    corpo = "Tamanho: 2 arquivos\nJá no código: não"
    falhas = conferir(repo, "base", True, titulo="revisão: 001", corpo=corpo).falhas
    assert not any("Tamanho:" in f for f in falhas)


def test_autor_do_agente() -> None:
    assert raias.do_agente("antigravity")
    assert raias.do_agente("antigravity-bot")
    assert not raias.do_agente("frayel")
