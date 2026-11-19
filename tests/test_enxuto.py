"""O repositório fica enxuto: nada de código, script ou teste sem uso.

Em 19/11 havia ~500 linhas sem uso: o placar antigo do Consultor (substituído
na tela por cálculo próprio em `app/main.py`), os gravadores da instrumentação
de antes da spec 073b, um script de relatório que nenhuma sessão chamava, e os
testes que só exercitavam esse código. Nada os chamava em produção, e os
testes os mantinham vivos.

A regra 11 do `devagent/conferir_pr.py` cuida da raiz e dos relatórios; este
teste cuida do código do produto.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

vulture = pytest.importorskip("vulture")

RAIZ = Path(__file__).resolve().parents[1]

# Funções sem uso em produção que ficam de propósito. Cada uma com o motivo;
# acrescentar aqui exige o mesmo cuidado que apagar.
PERMITIDAS = {
    # Zeram estado de módulo entre testes (cache, registro, conexão).
    "limpar": "reinicia o registro entre testes",
    "limpar_cache": "reinicia o cache do MT5 entre testes",
    "limpar_status_fontes": "reinicia o estado das fontes entre testes",
    "reset_db_init": "reinicia a criação do banco entre testes",
    # Leitores que os testes de aceite usam para conferir o que foi gravado.
    "ler_serie": "lê series_diarias no tests/test_aceite_179.py",
    "get_materias": "lê as matérias nos testes do Consultor",
    "get_latest_gemini_validacao": "lê a validação no tests/test_aceite_119b.py",
}


def test_sem_funcao_ou_classe_sem_uso() -> None:
    v = vulture.Vulture(ignore_decorators=["@app.*"])
    v.scavenge([str(RAIZ / "app"), str(RAIZ / "scripts")], exclude=["*/tests/*"])
    sem_uso = [
        f"{Path(i.filename).relative_to(RAIZ)}:{i.first_lineno} {i.typ} {i.name}"
        for i in v.get_unused_code(min_confidence=60)
        if i.typ in ("function", "class", "method", "property")
        and i.name not in PERMITIDAS
    ]
    assert not sem_uso, (
        "Código sem uso: apague (e os testes que só o exercitam) ou, se ele "
        "precisa ficar, ponha o nome em PERMITIDAS com o motivo:\n" + "\n".join(sem_uso)
    )


def test_permitidas_ainda_existem() -> None:
    """Exceção de função que já saiu do código também sai da lista."""
    v = vulture.Vulture(ignore_decorators=["@app.*"])
    v.scavenge([str(RAIZ / "app")], exclude=["*/tests/*"])
    nomes = {i.name for i in v.get_unused_code(min_confidence=60)}
    assert set(PERMITIDAS) <= nomes, set(PERMITIDAS) - nomes


def test_todo_script_tem_quem_o_chame() -> None:
    """Script em scripts/ é chamado pelo Makefile ou por um workflow."""
    versionados = subprocess.run(
        ["git", "ls-files", "scripts"], cwd=RAIZ, capture_output=True, text=True
    ).stdout.split()
    chamadores = (RAIZ / "Makefile").read_text(encoding="utf-8") + "".join(
        p.read_text(encoding="utf-8")
        for p in (RAIZ / ".github" / "workflows").glob("*.yml")
    )
    orfaos = [s for s in versionados if Path(s).name not in chamadores]
    assert not orfaos, f"Scripts que nada chama: {orfaos}"
