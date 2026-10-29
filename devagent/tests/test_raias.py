"""Raias paralelas (ADR 021): quem pode escrever onde, e quando cada uma roda."""

from __future__ import annotations

import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from devagent import conferir_pr, fila_specs, guardiao_prs, raias
from devagent.adaptadores import jules
from devagent.auditoria import achados_para_issues
from devagent.conferir_pr import conferir

AGORA = datetime(2026, 10, 23, 16, 0, tzinfo=timezone.utc)


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


def test_numeros_reservados_vem_do_prompt_das_sessoes_recentes() -> None:
    sessoes = [
        {"createTime": "2026-10-23T15:00:00Z", "prompt": "... use o número 091: ..."},
        {"createTime": "2026-10-22T01:00:00Z", "prompt": "... use o número 088: ..."},
        {"createTime": "2026-10-23T15:30:00Z", "prompt": "sem reserva"},
    ]
    assert jules.numeros_reservados(sessoes, AGORA) == {91}


# --- quem a rodada abre ----------------------------------------------------------


def _sessao(
    persona: str, criada: datetime, estado: str = "COMPLETED"
) -> dict[str, Any]:
    return {
        "name": f"sessions/{persona}",
        "title": jules.PERSONAS[persona]["titulo"],
        "createTime": criada.isoformat().replace("+00:00", "Z"),
        "updateTime": criada.isoformat().replace("+00:00", "Z"),
        "state": estado,
    }


def _decidir(
    sessoes: list[dict[str, Any]] | None = None,
    prontas: int = 2,
    em_revisao: int = 0,
    com_pr: set[str] | None = None,
    merges: int = 0,
) -> list[str]:
    caminhos = [Path(f"docs/specs/{n:03d}-x.md") for n in range(prontas)]
    return jules.raias_a_iniciar(
        sessoes or [],
        AGORA,
        caminhos,
        caminhos[:em_revisao],
        com_pr or set(),
        merges,
    )


def test_especificador_mantem_estoque_de_duas() -> None:
    # ADR 029: com 1, o desenvolvimento esperava a escrita e a revisão da próxima.
    assert "especificador" not in _decidir(prontas=3)
    assert "especificador" in _decidir(prontas=2)
    assert "especificador" in _decidir(prontas=1)
    assert "especificador" in _decidir(prontas=0)


def test_revisor_so_com_spec_esperando() -> None:
    assert "revisor" not in _decidir(em_revisao=0)
    assert "revisor" in _decidir(em_revisao=1)


def test_verificador_precisa_de_merge_e_de_intervalo() -> None:
    assert "verificador" not in _decidir(merges=0)
    assert "verificador" in _decidir(merges=2)
    recente = _sessao("verificador", AGORA - timedelta(minutes=30))
    assert "verificador" not in _decidir([recente], merges=2)
    antiga = _sessao("verificador", AGORA - timedelta(hours=2))
    assert "verificador" in _decidir([antiga], merges=2)


def test_raia_com_sessao_ativa_ou_pr_aberto_espera(monkeypatch) -> None:
    monkeypatch.setattr(jules, "estado_do_pr", lambda url: None)
    ativa = _sessao("revisor", AGORA - timedelta(minutes=10), "IN_PROGRESS")
    assert "revisor" not in _decidir([ativa], em_revisao=1)
    assert "revisor" not in _decidir(em_revisao=1, com_pr={raias.REVISAO})
    # O PR aberto de uma raia não trava as outras.
    assert _decidir(prontas=1, em_revisao=1, com_pr={raias.VERIFICACAO}, merges=1) == [
        "especificador",
        "revisor",
    ]


def test_sessao_do_desenvolvedor_nao_trava_as_raias() -> None:
    dev = _sessao("desenvolvedor", AGORA - timedelta(minutes=5), "IN_PROGRESS")
    assert _decidir([dev], prontas=1, em_revisao=1, merges=1) == [
        "especificador",
        "revisor",
        "verificador",
    ]


def test_rodada_das_raias_inicia_as_escolhidas(monkeypatch) -> None:
    iniciadas: list[str] = []
    monkeypatch.setattr(jules, "specs_prontas", lambda: [Path("docs/specs/084-x.md")])
    monkeypatch.setattr(jules, "fila_da_revisao", lambda prontas: prontas)
    monkeypatch.setattr(jules, "raias_com_pr_aberto", set)
    monkeypatch.setattr(jules, "spec_para_dividir", lambda prontas, issues: None)
    monkeypatch.setattr(jules, "issues_de_tentativa", list)
    monkeypatch.setattr(jules, "merges_do_desenvolvimento", lambda desde: [])
    monkeypatch.setattr(jules, "iniciar", lambda p, dry_run: iniciadas.append(p) or 0)
    jules.rodada_das_raias([], AGORA)
    assert iniciadas == ["especificador", "revisor"]


def test_revisor_abre_para_dividir_mesmo_sem_spec_a_revisar() -> None:
    escolhidas = jules.raias_a_iniciar([], AGORA, [], [], {"especificacao"}, 0, True)
    assert escolhidas == ["revisor"]


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


def test_prompt_do_revisor_aponta_a_spec(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(fila_specs, "revisao_desde", lambda: "084")
    _spec(tmp_path / "docs/specs", "084-crua.md", "ready")
    prompt = jules.prompt_de("revisor")
    assert prompt.startswith(jules.PERSONAS["revisor"]["prompt"])
    assert "docs/specs/084-crua.md" in prompt


def test_prompt_do_especificador_reserva_numero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("JULES_API_KEY", raising=False)
    _spec(tmp_path / "docs/specs", "083-a.md", "done")
    prompt = jules.prompt_de("especificador")
    assert "use o número 084" in prompt
    assert jules.NUMERO_RESERVADO.search(prompt)


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


def test_raia_respeita_teto_diario() -> None:
    sessoes = [
        {
            "title": jules.PERSONAS["revisor"]["titulo"],
            "state": "COMPLETED",
            "createTime": "2026-10-23T15:00:00Z",
        }
    ] * jules.TETO_DIARIO_DA_RAIA["revisor"]
    escolhidas = jules.raias_a_iniciar(
        sessoes, AGORA, [], [Path("x")], {"especificacao"}, 0
    )
    assert "revisor" not in escolhidas


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


def test_raia_da_sessao_vence_o_titulo() -> None:
    res = conferir_pr.Resultado()
    conferir_pr.conferir_raia_da_sessao(res, "especificacao", "Desenvolvedor · ciclo")
    assert res.falhas and "Desenvolvedor" in res.falhas[0]
    res = conferir_pr.Resultado()
    conferir_pr.conferir_raia_da_sessao(res, "especificacao", "Especificador · spec")
    assert res.falhas == []


def test_autor_do_agente() -> None:
    assert raias.do_agente("google-labs-jules[bot]")
    assert raias.do_agente("app/google-labs-jules")
    assert not raias.do_agente("frayel")


def test_verificacao_sem_achado_reprova(repo: Path) -> None:
    (repo / "docs/verificacao/relatorios").mkdir(parents=True)
    (repo / "docs/verificacao/relatorios/r.md").write_text("ok\n")
    falhas = conferir(
        repo, "base", True, titulo="verificação: 0 achados", sessao="", corpo=""
    ).falhas
    assert any("sem achado" in f for f in falhas)


def test_revisao_exige_conferencia_no_corpo(repo: Path) -> None:
    (repo / "docs/specs/001-a.md").write_text("---\nstatus: ready\nrevisada: x\n---\n")
    falhas = conferir(
        repo, "base", True, titulo="revisão: 001", sessao="", corpo="ok"
    ).falhas
    assert any("Tamanho:" in f for f in falhas)
    corpo = "Tamanho: 2 arquivos\nJá no código: não"
    falhas = conferir(
        repo, "base", True, titulo="revisão: 001", sessao="", corpo=corpo
    ).falhas
    assert not any("Tamanho:" in f for f in falhas)
