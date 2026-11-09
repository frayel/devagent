import subprocess
from pathlib import Path


def test_arquivos_e_simbolos_mortos_removidos():
    # 1. app/agendador_patched.py não pode existir
    assert not Path("app/agendador_patched.py").exists(), (
        "app/agendador_patched.py não foi removido"
    )

    # 2. app/main.py não deve definir verificar_credenciais nem security = HTTPBasic()
    conteudo_main = Path("app/main.py").read_text(encoding="utf-8")
    assert "def verificar_credenciais" not in conteudo_main, (
        "app/main.py ainda define verificar_credenciais"
    )
    assert "security = HTTPBasic" not in conteudo_main, (
        "app/main.py ainda define security = HTTPBasic"
    )


def test_logging_basicconfig_apenas_em_main():
    # 3. Nenhum arquivo em app/ fora de app/main.py pode conter logging.basicConfig
    arquivos_com_basicconfig = []
    for p in Path("app").rglob("*.py"):
        if p.as_posix() == "app/main.py":
            continue
        texto = p.read_text(encoding="utf-8")
        if "logging.basicConfig" in texto:
            arquivos_com_basicconfig.append(p.as_posix())

    assert not arquivos_com_basicconfig, (
        f"Arquivos em app/ ainda contêm logging.basicConfig: {arquivos_com_basicconfig}"
    )

    # Garante que app/main.py configura o log
    conteudo_main = Path("app/main.py").read_text(encoding="utf-8")
    assert "logging.basicConfig" in conteudo_main, (
        "app/main.py não configura logging.basicConfig"
    )


def test_arquivos_raiz_nao_versionados():
    # 4. test.db, commit_body.txt e demais arquivos mortos não podem estar no git ls-files
    arquivos_mortos = [
        "test.db",
        "commit_body.txt",
        "commit_description.txt",
        "generate_plan.sh",
        "screenshot_desktop.png",
        "telas_desktop.png",
        "verification.png",
    ]
    res = subprocess.run(
        ["git", "ls-files", *arquivos_mortos],
        capture_output=True,
        text=True,
        check=True,
    )
    versionados = [linha.strip() for linha in res.stdout.splitlines() if linha.strip()]
    assert not versionados, f"Arquivos mortos ainda versionados: {versionados}"


def test_gitignore_regras():
    # 5. .gitignore ignora *.db, *.png na raiz e commit_*.txt
    gitignore = Path(".gitignore").read_text(encoding="utf-8")
    linhas = [linha.strip() for linha in gitignore.splitlines() if linha.strip()]

    assert any("*.db" in linha for linha in linhas), (
        ".gitignore não possui regra para *.db"
    )
    assert any("*.png" in linha for linha in linhas), (
        ".gitignore não possui regra para *.png"
    )
    assert any("commit_*.txt" in linha for linha in linhas), (
        ".gitignore não possui regra para commit_*.txt"
    )
