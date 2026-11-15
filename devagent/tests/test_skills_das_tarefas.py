"""As tarefas agendadas chamam skills versionadas, e cada skill traz o essencial.

O prompt de cada tarefa é uma linha ("Rode a skill /revisor"). O que a sessão
precisa saber mora na skill e muda por PR. Em 14/11 a regra de conferir o alvo
antes do PR só existia no repositório, e duas sessões revisaram a mesma spec
(#847 e #848): este teste impede que uma skill de tarefa perca esses passos.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
SKILLS = RAIZ / ".claude" / "skills"

# skill -> (persona do `devagent.papel`, marcador da raia)
TAREFAS = {
    "ciclo": ("desenvolvedor", "desenvolvimento"),
    "revisor": ("revisor", "revisao"),
    "especificador": ("especificador", "especificacao"),
    "verificador": ("verificador", "verificacao"),
}


def _skill(nome: str) -> str:
    caminho = SKILLS / nome / "SKILL.md"
    if not SKILLS.is_dir():
        pytest.skip("projeto sem .claude/skills")
    assert caminho.is_file(), f"falta a skill da tarefa agendada: {caminho}"
    return caminho.read_text(encoding="utf-8")


@pytest.mark.parametrize("nome", TAREFAS)
def test_skill_da_tarefa_tem_cabecalho(nome: str) -> None:
    texto = _skill(nome)
    cabecalho = re.match(r"---\n(.*?)\n---\n", texto, re.S)
    assert cabecalho, f"{nome}: falta o cabeçalho YAML da skill"
    assert re.search(rf"^name:\s*{nome}\s*$", cabecalho.group(1), re.M)
    assert re.search(r"^description:\s*\S", cabecalho.group(1), re.M)


@pytest.mark.parametrize("nome", TAREFAS)
def test_skill_da_tarefa_traz_os_passos_essenciais(nome: str) -> None:
    persona, raia = TAREFAS[nome]
    texto = _skill(nome)
    assert "python -m devagent.estado_github" in texto
    assert "Ninguém acompanha esta sessão" in texto
    assert f"<!-- devagent:raia:{raia} -->" in texto
    if nome != "ciclo":
        assert f"python -m devagent.papel {persona}" in texto
    if nome != "verificador":
        assert f"python -m devagent.papel conferir {persona} NNN" in texto
