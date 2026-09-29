"""O instalador leva o núcleo para um projeto novo sem apagar nada."""

from devagent.instalar import instalar


def test_instala_nucleo_e_modelos(tmp_path):
    instalar(tmp_path)
    for caminho in [
        "devagent/CICLO.md",
        "devagent/protegidos.txt",
        "devagent/auditoria/nucleo.py",
        ".github/workflows/automerge.yml",
        "AGENTS.md",
        "PRODUTO.md",
        "devagent.toml",
        "Makefile",
        "docs/STATE.md",
    ]:
        assert (tmp_path / caminho).is_file(), caminho
    assert not list(tmp_path.rglob("__pycache__"))


def test_nao_sobrescreve(tmp_path):
    (tmp_path / "PRODUTO.md").write_text("meu produto", encoding="utf-8")
    saida = instalar(tmp_path)
    assert (tmp_path / "PRODUTO.md").read_text(encoding="utf-8") == "meu produto"
    assert any(linha.startswith("mantido") and "PRODUTO.md" in linha for linha in saida)


def test_dry_run_nao_escreve(tmp_path):
    instalar(tmp_path, dry_run=True)
    assert not any(tmp_path.iterdir())
