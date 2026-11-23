"""Regras de disciplina do ciclo (devagent/conferir_pr.py) num repositório de brinquedo."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from devagent.conferir_pr import conferir, entradas_correcoes

BACKLOG_COM_CORRECAO = """# Backlog

## Correções (prioridade sobre qualquer feature)

- **Defeito conhecido.** Implementar a spec `docs/specs/002-b.md`.

## Features

- ideia qualquer
"""

BACKLOG_SEM_CORRECAO = """# Backlog

## Correções (prioridade sobre qualquer feature)

## Features

- ideia qualquer
"""


# Relatório com o nome que as regras 9 e 11 aceitam: a hora UTC de agora.
RELATORIO = f"docs/runs/{datetime.now(timezone.utc):%Y-%m-%d-%H%M}.md"


def spec(numero: int, status: str) -> str:
    return f"---\nid: {numero:03d}\ntitulo: Spec {numero}\nstatus: {status}\n---\n\nTexto.\n"


def git(raiz: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=raiz, check=True, capture_output=True)


def escrever(raiz: Path, arquivos: dict[str, str]) -> None:
    for caminho, texto in arquivos.items():
        alvo = raiz / caminho
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(texto, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "t@t")
    git(tmp_path, "config", "user.name", "t")
    escrever(
        tmp_path,
        {
            "docs/specs/001-a.md": spec(1, "ready"),
            "docs/specs/002-b.md": spec(2, "ready"),
            "docs/BACKLOG.md": BACKLOG_SEM_CORRECAO,
            "docs/STATE.md": "# Estado\n",
            "CHANGELOG.md": "# Changelog\n",
            "tests/test_ok.py": "def test_ok():\n    pass\n",
        },
    )
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "base")
    git(tmp_path, "branch", "base")
    git(tmp_path, "checkout", "-q", "-b", "trabalho")
    return tmp_path


def fechar(
    repo: Path, numero: int = 1, changelog: bool = True, estado: bool = True
) -> None:
    arquivos = {f"docs/specs/{numero:03d}-{'ab'[numero - 1]}.md": spec(numero, "done")}
    if changelog:
        arquivos["CHANGELOG.md"] = f"# Changelog\n- feat: entrega (Spec {numero:03d})\n"
    if estado:
        arquivos["docs/STATE.md"] = f"# Estado\n- Spec {numero:03d}\n"
    escrever(repo, arquivos)


def test_pr_completo_passa(repo: Path) -> None:
    fechar(repo)
    assert conferir(repo, "base").falhas == []


def test_spec_in_progress_reprova(repo: Path) -> None:
    escrever(repo, {"docs/specs/001-a.md": spec(1, "in-progress")})
    falhas = conferir(repo, "base").falhas
    assert any("001-a.md" in f and "in-progress" in f for f in falhas)


def test_script_de_teste_fora_de_tests_reprova(repo: Path) -> None:
    escrever(repo, {"test_explorar.py": "print(1)\n"})
    falhas = conferir(repo, "base").falhas
    assert any("test_explorar.py" in f for f in falhas)


def test_teste_dentro_de_subpasta_tests_passa(repo: Path) -> None:
    escrever(repo, {"pacote/tests/test_x.py": "def test_x():\n    pass\n"})
    assert conferir(repo, "base").falhas == []


def test_spec_done_sem_changelog_reprova(repo: Path) -> None:
    fechar(repo, changelog=False)
    falhas = conferir(repo, "base").falhas
    assert any("CHANGELOG" in f and "spec 1" in f for f in falhas)


def test_changelog_precisa_citar_o_numero_certo(repo: Path) -> None:
    fechar(repo)
    escrever(repo, {"CHANGELOG.md": "# Changelog\n- feat: entrega (Spec 010)\n"})
    falhas = conferir(repo, "base").falhas
    assert any("CHANGELOG" in f for f in falhas)


def test_spec_done_sem_estado_reprova(repo: Path) -> None:
    fechar(repo, estado=False)
    falhas = conferir(repo, "base").falhas
    assert any("STATE.md" in f for f in falhas)


def test_correcao_pendente_impede_spec_nova(repo: Path) -> None:
    git(repo, "checkout", "-q", "base")
    escrever(repo, {"docs/BACKLOG.md": BACKLOG_COM_CORRECAO})
    git(repo, "commit", "-qam", "correcao")
    git(repo, "branch", "-f", "trabalho")
    git(repo, "checkout", "-q", "trabalho")
    fechar(repo, 1)
    falhas = conferir(repo, "HEAD").falhas
    assert any("Correções" in f for f in falhas)


def test_resolver_a_correcao_libera(repo: Path) -> None:
    git(repo, "checkout", "-q", "base")
    escrever(repo, {"docs/BACKLOG.md": BACKLOG_COM_CORRECAO})
    git(repo, "commit", "-qam", "correcao")
    git(repo, "checkout", "-q", "-B", "trabalho")
    fechar(repo, 2)
    escrever(repo, {"docs/BACKLOG.md": BACKLOG_SEM_CORRECAO})
    assert conferir(repo, "HEAD").falhas == []


def test_fechar_spec_ja_em_andamento_e_continuidade(repo: Path) -> None:
    git(repo, "checkout", "-q", "base")
    escrever(
        repo,
        {
            "docs/BACKLOG.md": BACKLOG_COM_CORRECAO,
            "docs/specs/001-a.md": spec(1, "in-progress"),
        },
    )
    git(repo, "commit", "-qam", "base com spec aberta")
    git(repo, "checkout", "-q", "-B", "trabalho")
    fechar(repo, 1)
    assert conferir(repo, "HEAD").falhas == []


def test_entrada_bloqueada_nao_conta() -> None:
    texto = BACKLOG_COM_CORRECAO.replace(
        "002-b.md`.", "002-b.md`. Aguarda issue `bloqueado` #9."
    )
    assert entradas_correcoes(texto, "Correções") == []


def test_sem_base_so_regras_da_arvore(repo: Path) -> None:
    fechar(repo, changelog=False, estado=False)
    res = conferir(repo, "ref-que-nao-existe-e-sem-origin")
    assert res.falhas == []
    assert res.avisos


def test_pr_vazio_reprova(repo: Path) -> None:
    falhas = conferir(repo, "base", exigir_alteracao=True).falhas
    assert any("não altera nenhum arquivo" in f for f in falhas)


def test_pr_vazio_so_reprova_quando_exigido(repo: Path, monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    assert conferir(repo, "base").falhas == []
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    assert conferir(repo, "base").falhas == []
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    assert any("não altera" in f for f in conferir(repo, "base").falhas)


def test_pr_com_alteracao_passa_mesmo_exigindo(repo: Path) -> None:
    fechar(repo)
    assert conferir(repo, "base", exigir_alteracao=True).falhas == []


def test_pr_so_de_registro_reprova(repo: Path, monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
    escrever(repo, {"docs/diarios/sentinel.md": "# Diário\n- nada a fazer\n"})
    escrever(repo, {RELATORIO: "# Relatório\n"})
    falhas = conferir(repo, "base", exigir_alteracao=True).falhas
    assert any("registros da execução" in f for f in falhas)


def test_registro_junto_com_entrega_passa(repo: Path) -> None:
    fechar(repo)
    escrever(repo, {"docs/diarios/sentinel.md": "# Diário\n- nada a fazer\n"})
    escrever(repo, {RELATORIO: "# Relatório\n"})
    assert conferir(repo, "base", exigir_alteracao=True).falhas == []


def test_registro_que_fecha_issue_passa(
    repo: Path, tmp_path_factory, monkeypatch
) -> None:
    evento = tmp_path_factory.mktemp("evento") / "evento.json"
    evento.write_text('{"pull_request": {"body": "Duplicada.\\n\\nCloses #12"}}')
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(evento))
    escrever(repo, {RELATORIO: "# Relatório\n"})
    assert conferir(repo, "base", exigir_alteracao=True).falhas == []


def test_registro_so_reprova_quando_exigido(repo: Path, monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    escrever(repo, {RELATORIO: "# Relatório\n"})
    assert conferir(repo, "base").falhas == []


def test_nome_do_relatorio_e_a_hora_utc_em_que_foi_escrito() -> None:
    from datetime import datetime, timezone

    from devagent.conferir_pr import hora_do_relatorio_errada

    escrito = datetime(2026, 11, 15, 0, 50, tzinfo=timezone.utc)
    assert hora_do_relatorio_errada("docs/runs/2026-11-15-0045.md", escrito) == ""
    # 15/11 00:50 UTC era 14/11 21:50 em Brasília: o nome 15-2129 mistura a
    # data de um fuso com a hora de outro e fica "no futuro" o dia inteiro.
    assert "00:50" not in hora_do_relatorio_errada(
        "docs/runs/2026-11-15-2129.md", escrito
    )
    assert "2026-11-15-0050" in hora_do_relatorio_errada(
        "docs/runs/2026-11-15-2129.md", escrito
    )
    # Hora de Brasília (3 h antes do UTC) também reprova.
    assert hora_do_relatorio_errada("docs/runs/2026-11-14-2150.md", escrito)
    assert hora_do_relatorio_errada(
        "docs/verificacao/relatorios/2026-11-14-2150.md", escrito
    )
    assert hora_do_relatorio_errada("docs/runs/notas-soltas.md", escrito) == ""


# Regra 11 (19/11): repositório enxuto. Havia 42 relatórios com nome fora do
# padrão, sobras de sessão na raiz e os diários em duas pastas idênticas.
def test_enxuto_reprova_relatorio_fora_do_padrao() -> None:
    from devagent.conferir_pr import Resultado, conferir_enxuto

    res = Resultado()
    conferir_enxuto(
        res,
        [
            "docs/runs/2026-11-19-1249.md",
            "docs/runs/108a_run.md",
            "docs/verificacao/relatorios/relatorio.md",
            "docs/verificacao/achados/qualquer-nome.md",
        ],
        {},
    )
    assert len(res.falhas) == 2
    assert "108a_run.md" in res.falhas[0]


def test_enxuto_reprova_pasta_aposentada_e_raiz_fora_da_lista() -> None:
    from devagent.conferir_pr import Resultado, conferir_enxuto

    res = Resultado()
    conferir_enxuto(
        res,
        ["README.md", "plan.md", ".jules/bolt.md", "app/main.py"],
        {"raiz": ["README.md"], "pastas_proibidas": [".jules/"]},
    )
    assert len(res.falhas) == 2
    assert any(".jules/bolt.md" in f for f in res.falhas)
    assert any("plan.md" in f for f in res.falhas)


def test_enxuto_sem_secao_nao_confere_a_raiz() -> None:
    from devagent.conferir_pr import Resultado, conferir_enxuto

    res = Resultado()
    conferir_enxuto(res, ["plan.md", "notas.txt"], {})
    assert res.falhas == []


# Regra 12 (23/11): a página de novidades só tinha uma entrada em 22/11; as
# correções visíveis não escreviam o arquivo.
NOVIDADES = {"arquivo": "app/novidades.json", "caminhos": ["app/"]}


@pytest.mark.parametrize(
    "titulo, corpo, alterados, reprova",
    [
        ("fix: o card volta", "", {"app/main.py"}, True),
        ("feat: card novo (spec 9)", "", {"app/templates/x.html"}, True),
        ("fix: o card volta", "", {"app/main.py", "app/novidades.json"}, False),
        ("fix: coletor", "Novidades: nenhuma, só log interno.", {"app/x.py"}, False),
        ("fix: teste", "", {"app/tests/test_x.py"}, False),
        ("refactor: laço", "", {"app/main.py"}, False),
        ("agent: regra", "", {"devagent/x.py"}, False),
        ("fix: doc", "", {"docs/STATE.md"}, False),
        ("", "", {"app/main.py"}, False),
    ],
)
def test_regra_12_novidades(
    titulo: str, corpo: str, alterados: set[str], reprova: bool
) -> None:
    from devagent.conferir_pr import Resultado, conferir_novidades

    res = Resultado()
    conferir_novidades(res, titulo, corpo, alterados, NOVIDADES)
    assert bool(res.falhas) is reprova
    if reprova:
        assert "app/novidades.json" in res.falhas[0]


def test_regra_12_sem_secao_nao_roda() -> None:
    from devagent.conferir_pr import Resultado, conferir_novidades

    res = Resultado()
    conferir_novidades(res, "fix: x", "", {"app/main.py"}, {})
    assert res.falhas == []
