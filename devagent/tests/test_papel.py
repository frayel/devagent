"""O papel da sessão: raia parada não deixa o desenvolvimento ocioso (ADR 033).

De 13/11 a 14/11 a fila inteira esperou a raia de revisão, que ninguém
acionava, e o desenvolvimento entregou dezessete PRs seguidos sem fechar
nenhuma spec. Estes testes fixam a decisão que teria evitado isso.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from devagent import fila_specs, papel


def _spec(pasta: Path, nome: str, revisada: bool = False) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    campo = "revisada: 2026-01-01\n" if revisada else ""
    caminho = pasta / nome
    caminho.write_text(f"---\nid: 1\nstatus: ready\n{campo}---\n", encoding="utf-8")
    return caminho


@pytest.fixture
def raiz(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(fila_specs, "revisao_desde", lambda: "084")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _pr(raia: str, ci: str = "passou", merge: str = "clean", **mais) -> dict:
    return {"numero": 9, "branch": "b", "raia": raia, "ci": ci, "merge": merge, **mais}


def test_fila_inteira_esperando_revisao_vira_sessao_do_revisor(raiz: Path) -> None:
    a = _spec(raiz / "docs/specs", "144-a.md")
    b = _spec(raiz / "docs/specs", "145-b.md")
    p = papel.decidir([a, b], [], [], raiz=raiz)
    assert p.persona == papel.REVISOR
    assert "docs/specs/144-a.md" in p.alvo
    assert "atua como Revisor" in p.frase()


def test_spec_revisada_na_fila_e_do_desenvolvedor(raiz: Path) -> None:
    a = _spec(raiz / "docs/specs", "144-a.md", revisada=True)
    b = _spec(raiz / "docs/specs", "145-b.md")
    p = papel.decidir([a, b], [], [], raiz=raiz)
    assert p.persona == papel.DESENVOLVEDOR
    assert not p.alvo


@pytest.mark.parametrize(
    "issues, prs, quebrada",
    [
        ([{"numero": 3, "titulo": "x", "labels": ["prioridade"]}], [], False),
        ([{"numero": 3, "titulo": "x", "labels": ["deploy-falhou"]}], [], False),
        ([], [_pr("desenvolvimento", do_agente=True)], False),
        ([], [], True),
    ],
)
def test_trabalho_de_produto_vem_antes_de_assumir_outra_raia(
    raiz: Path, issues: list, prs: list, quebrada: bool
) -> None:
    a = _spec(raiz / "docs/specs", "144-a.md")
    p = papel.decidir([a], issues, prs, quebrada, raiz=raiz)
    assert p.persona == papel.DESENVOLVEDOR


def test_pr_de_revisao_aberto_e_saudavel_nao_duplica_a_revisao(raiz: Path) -> None:
    specs = [_spec(raiz / "docs/specs", f"14{n}-x.md") for n in range(4, 8)]
    p = papel.decidir(specs, [], [_pr("revisao")], raiz=raiz)
    assert p.persona == papel.DESENVOLVEDOR


def test_pr_de_revisao_travado_vira_a_tarefa_do_revisor(raiz: Path) -> None:
    a = _spec(raiz / "docs/specs", "144-a.md")
    travado = _pr("revisao", ci="falhou: disciplina")
    p = papel.decidir([a], [], [travado], raiz=raiz)
    assert p.persona == papel.REVISOR
    assert "#9" in p.alvo and "destravá-lo" in p.alvo
    assert "destravá-lo" in papel.para_persona(papel.REVISOR, [a], [], [travado]).alvo


def test_fila_no_fim_vira_sessao_do_especificador(raiz: Path) -> None:
    p = papel.decidir([], [], [], raiz=raiz)
    assert p.persona == papel.ESPECIFICADOR
    assert "número 001" in p.alvo
    # Com PR `spec:` aberto, a spec nova já está a caminho.
    assert papel.decidir([], [], [_pr("especificacao")], raiz=raiz).persona == (
        papel.DESENVOLVEDOR
    )


def test_spec_com_tentativa_fechada_vai_para_o_revisor_dividir(raiz: Path) -> None:
    a = _spec(raiz / "docs/specs", "144-a.md", revisada=True)
    issues = [{"numero": 7, "titulo": "spec 144", "labels": ["tentativa-falhou"]}]
    p = papel.decidir([a], issues, [], raiz=raiz)
    assert p.persona == papel.REVISOR
    assert "dividir" in p.alvo and "Closes #7" in p.alvo


def test_entregas_sem_spec_conta_so_o_desenvolvimento() -> None:
    titulos = [
        "agent: a (#5)",
        "revisão: spec 144 (#4)",
        "fix: b (#3)",
        "docs: c (#2)",
        "feat: d (143) (#1)",
        "agent: antigo (#0)",
    ]
    assert papel.entregas_sem_spec(titulos) == 3


def test_fila_travada_sem_raia_para_assumir_avisa_o_desenvolvedor(raiz: Path) -> None:
    specs = [_spec(raiz / "docs/specs", f"14{n}-x.md") for n in range(4, 8)]
    titulos = [f"agent: melhoria {n}" for n in range(papel.LIMITE_SEM_SPEC)]
    p = papel.decidir(specs, [], [_pr("revisao")], titulos_da_main=titulos, raiz=raiz)
    assert p.persona == papel.DESENVOLVEDOR
    assert "FILA TRAVADA" in p.frase()
    assert "encerre sem PR" in p.frase()
    # Uma entrega de spec recente desfaz o alarme.
    p = papel.decidir(
        specs, [], [_pr("revisao")], titulos_da_main=["feat: x (1)"], raiz=raiz
    )
    assert not p.frase()


def test_persona_nomeada_sem_trabalho_tem_alvo_vazio(raiz: Path) -> None:
    a = _spec(raiz / "docs/specs", "144-a.md", revisada=True)
    cheias = [a] * (papel.FILA_PARA_ESPECIFICAR + 1)
    assert not papel.para_persona(papel.REVISOR, [a], [], []).alvo
    assert not papel.para_persona(papel.ESPECIFICADOR, cheias, [], []).alvo
    assert not papel.para_persona(papel.VERIFICADOR, [a], [], [], merges=[]).alvo
    alvo = papel.para_persona(papel.VERIFICADOR, [a], [], [], merges=["fix: x"]).alvo
    assert "fix: x" in alvo


def test_ultima_verificacao_nunca_passa_da_janela(tmp_path: Path) -> None:
    pasta = tmp_path / "docs/verificacao/relatorios"
    pasta.mkdir(parents=True)
    (pasta / "2020-01-01-0000.md").write_text("x", encoding="utf-8")
    from datetime import datetime, timedelta, timezone

    desde = papel.desde_a_ultima_verificacao(tmp_path)
    idade = datetime.now(timezone.utc) - desde
    assert idade <= papel.JANELA_DA_VERIFICACAO + timedelta(minutes=1)


SPEC_PRONTA = "---\nid: 150\nstatus: ready\n---\n"
SPEC_REVISADA = "---\nid: 150\nstatus: ready\nrevisada: 2026-11-14\n---\n"


def _aberto(titulo: str, raia: str) -> dict:
    return {"numero": 847, "titulo": titulo, "raia": raia}


def test_revisor_que_chega_depois_nao_abre_segunda_revisao() -> None:
    # 14/11 21:38: o #847 entrou um minuto depois de a tarefa do Revisor
    # escolher a mesma spec.
    pr = _aberto("revisão: spec 150 · premissa corrigida", "revisao")
    assert "#847" in papel.alvo_ocupado(papel.REVISOR, "150", [pr], SPEC_PRONTA)
    assert "já foi revisada" in papel.alvo_ocupado(
        papel.REVISOR, "150", [], SPEC_REVISADA
    )
    assert papel.alvo_ocupado(papel.REVISOR, "150", [], SPEC_PRONTA) == ""


def test_desenvolvedor_confere_a_spec_e_os_prs_da_raia() -> None:
    assert papel.alvo_ocupado(papel.DESENVOLVEDOR, "150", [], SPEC_REVISADA) == ""
    pr = _aberto("feat: o radar vazio não ocupa card (spec 150)", "desenvolvimento")
    assert "#847" in papel.alvo_ocupado(papel.DESENVOLVEDOR, "150", [pr], SPEC_REVISADA)
    outro = _aberto("fix: algo da 1500 e #150", "desenvolvimento")
    assert papel.alvo_ocupado(papel.DESENVOLVEDOR, "150", [outro], SPEC_REVISADA) == ""
    feita = SPEC_REVISADA.replace("ready", "done")
    assert "`done`" in papel.alvo_ocupado(papel.DESENVOLVEDOR, "150", [], feita)


def test_especificador_nao_reusa_numero_ocupado() -> None:
    assert papel.alvo_ocupado(papel.ESPECIFICADOR, "152", [], None) == ""
    assert "ocupado" in papel.alvo_ocupado(papel.ESPECIFICADOR, "152", [], "x")
    pr = _aberto("spec: 152 · nova", "especificacao")
    assert "#847" in papel.alvo_ocupado(papel.ESPECIFICADOR, "152", [pr], None)
