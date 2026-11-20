"""Classe usada num template precisa fazer alguma coisa no navegador (spec 187).

Uma classe estática de `app/templates/*.html` tem de ter seletor no CSS
(`app/static/*.css` ou um `<style>` dos templates) ou aparecer no JS
(`app/static/*.js`). As que hoje não fazem nada ficam em
`SEM_ESTILO_CONHECIDAS`, que só encolhe: classe nova sem estilo reprova, e
exceção que deixou de valer (a classe sumiu, ganhou seletor ou passou ao JS)
também reprova até a linha sair da lista.

Classes montadas em tempo de execução (`g-cor-{{ n }}`) e as postas pelo JS
ficam fora: o teste não as enxerga.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TEMPLATES = RAIZ / "app" / "templates"
ESTATICOS = RAIZ / "app" / "static"

_DIVIDA = "dívida medida na spec 187"

SEM_ESTILO_CONHECIDAS: dict[str, str] = {
    # index.html
    "aba-densidade": _DIVIDA,
    "alerta-vazio": _DIVIDA,
    "aviso-vazio": _DIVIDA,
    "conteudo-centralizado": _DIVIDA,
    "dado-indisponivel": _DIVIDA,
    "dado-vazio": _DIVIDA,
    "destaque-texto": _DIVIDA,
    "dir": _DIVIDA,
    "direita": _DIVIDA,
    "em-revisao": _DIVIDA,
    "espaco-topo-curto": _DIVIDA,
    "esq": _DIVIDA,
    "estado": _DIVIDA,
    "icone": _DIVIDA,
    "item-revisao": _DIVIDA,
    "kpi-group": _DIVIDA,
    "legenda": _DIVIDA,
    "manchete-container": _DIVIDA,
    "negativo": _DIVIDA,
    "normal": _DIVIDA,
    "numero": _DIVIDA,
    "positivo": _DIVIDA,
    "radares-sem-leitura": _DIVIDA,
    "ranking": _DIVIDA,
    "rodape-ausentes": _DIVIDA,
    "selo-revisao": _DIVIDA,
    "tabela-compacta": _DIVIDA,
    "texto-2": _DIVIDA,
    "vazia": _DIVIDA,
    "visao-micro": _DIVIDA,
    # index.html e componentes.html
    "selo-desatualizado": _DIVIDA,
    # componentes.html
    "mare-sem-curva": _DIVIDA,
    # base.html
    "aviso-dados": _DIVIDA,
    "aviso-legal": _DIVIDA,
    "espacador-direita": _DIVIDA,
    # consultor.html
    "badge": _DIVIDA,
    "badge-negativo": _DIVIDA,
    "badge-positivo": _DIVIDA,
    "lista-opinioes": _DIVIDA,
    "rodape-painel": _DIVIDA,
    "status-neutro": _DIVIDA,
    "tabela-sem-sinal": _DIVIDA,
    # sistema.html
    "checagem-corpo": _DIVIDA,
}

_ATRIBUTO_CLASS = re.compile(r"""(?<![\w-])class=(?:"([^"]*)"|'([^']*)')""")
_EXPRESSAO = re.compile(r"\{\{.*?\}\}", re.S)
_BLOCO = re.compile(r"\{%.*?%\}", re.S)
_NOME = re.compile(r"^[a-z][a-z0-9-]*$")
_ESTILO = re.compile(r"<style[^>]*>(.*?)</style>", re.S | re.I)
_DECLARACAO = re.compile(r"\{[^{}]*\}")
_SELETOR = re.compile(r"\.([a-zA-Z][\w-]*)")


def sem_expressoes(valor: str) -> str:
    """Passo 1: cada `{{ ... }}` vira um marcador sem espaço."""
    return _EXPRESSAO.sub("\x00", valor)


def sem_blocos(valor: str) -> str:
    """Passo 2: cada `{% ... %}` vira um espaço, e o texto entre eles fica."""
    return _BLOCO.sub(" ", valor)


def nomes_validos(valor: str) -> set[str]:
    """Passo 3: só os pedaços que são nome de classe estática."""
    return {parte for parte in valor.split() if _NOME.match(parte)}


def classes_do_atributo(valor: str) -> set[str]:
    return nomes_validos(sem_blocos(sem_expressoes(valor)))


def classes_dos_templates(textos: Mapping[str, str]) -> dict[str, set[str]]:
    """Classe estática -> templates onde ela aparece."""
    usos: dict[str, set[str]] = {}
    for nome, texto in textos.items():
        for casamento in _ATRIBUTO_CLASS.finditer(texto):
            valor = casamento.group(1)
            if valor is None:
                valor = casamento.group(2)
            for classe in classes_do_atributo(valor):
                usos.setdefault(classe, set()).add(nome)
    return usos


def estilos_dos_templates(textos: Iterable[str]) -> str:
    return "\n".join(bloco for texto in textos for bloco in _ESTILO.findall(texto))


def seletores_do_css(texto: str) -> set[str]:
    """Seletores de classe; uma passada só, para o `@media` não sumir."""
    return set(_SELETOR.findall(_DECLARACAO.sub("", texto)))


def citadas_no_js(nomes: Iterable[str], texto: str) -> set[str]:
    """Os nomes que aparecem no JS como palavra inteira (sem `_` nem `-` colado)."""
    return {
        nome
        for nome in nomes
        if re.search(rf"(?<![\w-]){re.escape(nome)}(?![\w-])", texto)
    }


def sem_estilo(usos: Mapping[str, set[str]], css: str, js: str) -> set[str]:
    nomes = set(usos)
    return nomes - seletores_do_css(css) - citadas_no_js(nomes, js)


def problemas(
    usos: Mapping[str, set[str]],
    css: str,
    js: str,
    conhecidas: Mapping[str, str],
) -> list[str]:
    """Mensagens de falha: classe nova sem estilo e exceção vencida."""
    atuais = sem_estilo(usos, css, js)
    mensagens = [
        f"classe `{classe}` em {', '.join(sorted(usos[classe]))} não tem efeito: "
        "dê um seletor em `app/static/tema.css`, use uma classe que já existe, ou, "
        "se for gancho de JS ou de teste, registre em `SEM_ESTILO_CONHECIDAS` "
        "com o motivo"
        for classe in sorted(atuais - set(conhecidas))
    ]
    mensagens += [
        f"exceção vencida: `{classe}` não está mais sem estilo (sumiu dos "
        "templates, ganhou seletor ou aparece no JS); tire a linha de "
        "`SEM_ESTILO_CONHECIDAS`"
        for classe in sorted(set(conhecidas) - atuais)
    ]
    return mensagens


def _arquivos_reais() -> tuple[dict[str, str], str, str]:
    templates = {
        p.name: p.read_text(encoding="utf-8") for p in sorted(TEMPLATES.glob("*.html"))
    }
    css = "\n".join(
        p.read_text(encoding="utf-8") for p in sorted(ESTATICOS.glob("*.css"))
    )
    css += "\n" + estilos_dos_templates(templates.values())
    js = "\n".join(
        p.read_text(encoding="utf-8") for p in sorted(ESTATICOS.glob("*.js"))
    )
    return templates, css, js


def test_toda_classe_dos_templates_faz_alguma_coisa():
    templates, css, js = _arquivos_reais()
    erros = problemas(classes_dos_templates(templates), css, js, SEM_ESTILO_CONHECIDAS)
    assert not erros, "\n".join(erros)


def test_lista_de_excecoes_nao_cresce_alem_da_medida():
    assert len(SEM_ESTILO_CONHECIDAS) <= 43
