"""A fronteira entre núcleo e projeto.

O núcleo (devagent/) é reaproveitado em outros projetos, então não pode saber
nada do produto. Este teste reprova o CI se algum arquivo do núcleo citar um
termo do domínio listado em devagent.toml ([projeto] termos_do_dominio).

Se o teste falhar num PR seu: o conhecimento é do produto e vai para
PRODUTO.md, docs/ ou auditoria/. Se a regra for de processo, escreva-a de
forma genérica e deixe o exemplo concreto no projeto.
"""

from __future__ import annotations

import re
from pathlib import Path

from devagent.config import PROJETO, carregar

NUCLEO = Path(__file__).resolve().parent.parent
EXTENSOES = {".py", ".md", ".txt", ".sh", ".toml", ".yml", ".yaml"}


def arquivos_do_nucleo() -> list[Path]:
    return sorted(
        p
        for p in NUCLEO.rglob("*")
        if p.is_file() and p.suffix in EXTENSOES and "__pycache__" not in p.parts
    )


def termos() -> list[str]:
    return [t for t in PROJETO.get("termos_do_dominio", []) if t.strip()]


def test_existem_termos_do_dominio_configurados():
    assert termos(), "defina [projeto] termos_do_dominio no devagent.toml"


def test_nucleo_nao_cita_o_produto():
    padrao = re.compile(
        r"(?<!\w)(" + "|".join(re.escape(t) for t in termos()) + r")(?!\w)",
        re.IGNORECASE,
    )
    violacoes = []
    for arq in arquivos_do_nucleo():
        texto = arq.read_text(encoding="utf-8", errors="replace")
        for n, linha in enumerate(texto.splitlines(), 1):
            m = padrao.search(linha)
            if m:
                violacoes.append(f"{arq.relative_to(NUCLEO.parent)}:{n}: {m.group(0)}")
    assert not violacoes, "O núcleo cita o produto:\n" + "\n".join(violacoes)


def test_nome_do_produto_fora_do_nucleo():
    nome = PROJETO.get("nome", "")
    assert nome
    for arq in arquivos_do_nucleo():
        assert nome not in arq.read_text(encoding="utf-8", errors="replace"), arq


def test_config_padrao_sem_arquivo(tmp_path):
    cfg = carregar(tmp_path / "inexistente.toml")
    assert cfg["verificacao"]["verify"] == "make verify"
    assert cfg["projeto"]["termos_do_dominio"] == []
