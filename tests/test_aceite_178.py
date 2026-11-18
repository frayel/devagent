"""Spec 178: teste que não confere nada reprova o CI.

Lê com `ast` (e `tokenize`, para os comentários) todos os `tests/**/*.py`, sem
importar os módulos, e reprova, com arquivo e linha:

1. função `test_*` (de módulo ou de classe, não fixture) sem conferência;
2. `pass` num corpo com mais de um comando, dentro de função `test_*`;
3. linha de comentário que começa com `assert`;
4. `assert len(...) >= 0`, que nunca falha.

Conta como conferência: `assert`, `raise`, `pytest.raises/warns/fail/skip`,
método `assert_*` (mocks) ou chamada a função do mesmo módulo, ou importada por
nome de outro arquivo de `tests/`, que confira pela mesma regra.
"""

from __future__ import annotations

import ast
import io
import re
import tokenize
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

# "arquivo::nome" -> motivo. No máximo 3 entradas, todas apontando para testes
# que existem. Só para teste cuja promessa é "não levanta" e que não chama
# nada que confira.
SEM_CONFERENCIA: dict[str, str] = {}

LIMITE_SEM_CONFERENCIA = 3

PYTEST_CONFERE = {"raises", "warns", "fail", "skip"}
COMENTARIO_ASSERT = re.compile(r"^\s*#[\s#]*assert\b")


class _Modulo:
    def __init__(self, caminho: str, fonte: str) -> None:
        self.caminho = caminho
        self.fonte = fonte
        self.arvore = ast.parse(fonte, filename=caminho)
        self.funcoes: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        self.importadas: dict[str, tuple[str, str]] = {}
        for no in self.arvore.body:
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.funcoes[no.name] = no
        for no in ast.walk(self.arvore):
            if isinstance(no, ast.ImportFrom):
                destino = self._resolver(no)
                if destino is None:
                    continue
                for alias in no.names:
                    self.importadas[alias.asname or alias.name] = (destino, alias.name)

    def _resolver(self, no: ast.ImportFrom) -> str | None:
        """Caminho (relativo à raiz) do arquivo de `tests/` importado, ou None."""
        modulo = no.module or ""
        if no.level:
            base = Path(self.caminho).parent
            for _ in range(no.level - 1):
                base = base.parent
            partes = [p for p in modulo.split(".") if p]
            return (base.joinpath(*partes)).as_posix() + ".py" if partes else None
        if modulo.startswith("tests."):
            return "/".join(modulo.split(".")) + ".py"
        return None


def _eh_fixture(funcao: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for decorador in funcao.decorator_list:
        alvo = decorador.func if isinstance(decorador, ast.Call) else decorador
        nome = alvo.attr if isinstance(alvo, ast.Attribute) else getattr(alvo, "id", "")
        if nome == "fixture":
            return True
    return False


def _so_marcador(funcao: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Corpo que só chama `exigir_spec_done(...)` (ADR 018), docstring à parte."""
    corpo = [
        c
        for c in funcao.body
        if not (isinstance(c, ast.Expr) and isinstance(c.value, ast.Constant))
    ]
    return bool(corpo) and all(
        isinstance(c, ast.Expr)
        and isinstance(c.value, ast.Call)
        and isinstance(c.value.func, ast.Name)
        and c.value.func.id == "exigir_spec_done"
        for c in corpo
    )


class Verificador:
    def __init__(self, fontes: dict[str, str]) -> None:
        self.modulos = {
            caminho: _Modulo(caminho, fonte) for caminho, fonte in fontes.items()
        }
        self._cache: dict[tuple[str, str], bool] = {}

    def confere(
        self, caminho: str, nome: str, visitados: frozenset = frozenset()
    ) -> bool:
        chave = (caminho, nome)
        if chave in self._cache:
            return self._cache[chave]
        if chave in visitados:
            return False
        modulo = self.modulos.get(caminho)
        if modulo is None:
            return False
        if nome in modulo.funcoes:
            resultado = self._corpo_confere(
                modulo, modulo.funcoes[nome], visitados | {chave}
            )
        elif nome in modulo.importadas:
            destino, original = modulo.importadas[nome]
            resultado = self.confere(destino, original, visitados | {chave})
        else:
            return False
        self._cache[chave] = resultado
        return resultado

    def _corpo_confere(
        self, modulo: _Modulo, funcao: ast.AST, visitados: frozenset
    ) -> bool:
        for no in ast.walk(funcao):
            if isinstance(no, (ast.Assert, ast.Raise)):
                return True
            if not isinstance(no, ast.Call):
                continue
            alvo = no.func
            if isinstance(alvo, ast.Attribute):
                if alvo.attr.startswith("assert_"):
                    return True
                if (
                    isinstance(alvo.value, ast.Name)
                    and alvo.value.id == "pytest"
                    and alvo.attr in PYTEST_CONFERE
                ):
                    return True
            elif isinstance(alvo, ast.Name):
                if alvo.id in (
                    modulo.funcoes.keys() | modulo.importadas.keys()
                ) and self.confere(modulo.caminho, alvo.id, visitados):
                    return True
        return False

    def testes(self, modulo: _Modulo):
        for no in modulo.arvore.body:
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield no.name, no
            elif isinstance(no, ast.ClassDef):
                for item in no.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        yield f"{no.name}.{item.name}", item

    def violacoes(self, excecoes: dict[str, str] | None = None) -> list[str]:
        excecoes = excecoes or {}
        saida: list[str] = []
        for caminho, modulo in sorted(self.modulos.items()):
            for nome, funcao in self.testes(modulo):
                if not funcao.name.startswith("test_") or _eh_fixture(funcao):
                    continue
                # Regra 1.2: pass solto num corpo com mais de um comando.
                for no in ast.walk(funcao):
                    for campo in ("body", "orelse", "finalbody"):
                        corpo = getattr(no, campo, None)
                        if isinstance(corpo, list) and len(corpo) > 1:
                            for comando in corpo:
                                if isinstance(comando, ast.Pass):
                                    saida.append(
                                        f"{caminho}:{comando.lineno} pass solto em {nome}"
                                    )
                # Regra 1.1: sem conferência.
                if f"{caminho}::{nome}" in excecoes or _so_marcador(funcao):
                    continue
                if not self._corpo_confere(
                    modulo, funcao, frozenset({(caminho, nome)})
                ):
                    saida.append(f"{caminho}:{funcao.lineno} {nome} sem conferência")
            # Regra 1.4: assert len(...) >= 0.
            for no in ast.walk(modulo.arvore):
                if (
                    isinstance(no, ast.Assert)
                    and isinstance(no.test, ast.Compare)
                    and isinstance(no.test.left, ast.Call)
                    and isinstance(no.test.left.func, ast.Name)
                    and no.test.left.func.id == "len"
                    and len(no.test.ops) == 1
                    and isinstance(no.test.ops[0], ast.GtE)
                    and isinstance(no.test.comparators[0], ast.Constant)
                    and no.test.comparators[0].value == 0
                ):
                    saida.append(
                        f"{caminho}:{no.lineno} assert len(...) >= 0 nunca falha"
                    )
            # Regra 1.3: assert comentado (só comentários de verdade, não strings).
            for token in tokenize.generate_tokens(io.StringIO(modulo.fonte).readline):
                if token.type == tokenize.COMMENT and COMENTARIO_ASSERT.match(
                    token.line
                ):
                    saida.append(f"{caminho}:{token.start[0]} assert comentado")
        return saida

    def existe(self, chave: str) -> bool:
        caminho, _, nome = chave.partition("::")
        modulo = self.modulos.get(caminho)
        return modulo is not None and any(n == nome for n, _ in self.testes(modulo))


def _fontes_do_repositorio() -> dict[str, str]:
    return {
        arquivo.relative_to(RAIZ).as_posix(): arquivo.read_text(encoding="utf-8")
        for arquivo in sorted((RAIZ / "tests").rglob("*.py"))
    }


# ---------------------------------------------------------------- repositório


def test_nenhum_teste_sem_conferencia_no_repositorio():
    verificador = Verificador(_fontes_do_repositorio())
    violacoes = verificador.violacoes(SEM_CONFERENCIA)
    assert not violacoes, "Testes que não conferem nada:\n" + "\n".join(violacoes)


def test_sem_conferencia_e_curta_e_aponta_para_testes_que_existem():
    assert len(SEM_CONFERENCIA) <= LIMITE_SEM_CONFERENCIA
    verificador = Verificador(_fontes_do_repositorio())
    for chave, motivo in SEM_CONFERENCIA.items():
        assert motivo.strip(), f"{chave} sem motivo"
        assert verificador.existe(chave), f"{chave} não existe"


# ------------------------------------------------------- casos do verificador


def _violacoes(fontes: dict[str, str]) -> list[str]:
    return Verificador(fontes).violacoes()


@pytest.mark.parametrize(
    ("fonte", "esperado"),
    [
        ("def test_b():\n    calcular()\n", "tests/x.py:1 test_b sem conferência"),
        (
            "def test_b():\n    calcular()\n    pass\n",
            "tests/x.py:3 pass solto em test_b",
        ),
        (
            "def test_c():\n    x = 1\n    # assert x == 1\n",
            "tests/x.py:3 assert comentado",
        ),
        (
            "def test_c():\n    x = 1\n    # # assert x\n",
            "tests/x.py:3 assert comentado",
        ),
        (
            "def test_d():\n    assert len([]) >= 0\n",
            "tests/x.py:2 assert len(...) >= 0 nunca falha",
        ),
        (
            "class TestX:\n    def test_m(self):\n        calcular()\n",
            "tests/x.py:2 TestX.test_m sem conferência",
        ),
    ],
)
def test_verificador_reprova(fonte, esperado):
    assert esperado in _violacoes({"tests/x.py": fonte})


def test_exemplo_da_spec():
    fonte = (
        "def _conferir(x):\n"
        "    assert x == 2\n"
        "\n"
        "def test_a():\n"
        "    _conferir(1 + 1)\n"
        "\n"
        "def test_b():\n"
        "    calcular()\n"
        "    pass\n"
    )
    assert _violacoes({"tests/x.py": fonte}) == [
        "tests/x.py:9 pass solto em test_b",
        "tests/x.py:7 test_b sem conferência",
    ]


@pytest.mark.parametrize(
    "fonte",
    [
        "def _conferir(x):\n    assert x\n\ndef test_a():\n    _conferir(1)\n",
        "import pytest\n\ndef test_a():\n    with pytest.raises(ValueError):\n        int('x')\n",
        "def test_a(mocker):\n    m = mocker.Mock()\n    m()\n    m.assert_called_once()\n",
        "from devagent.aceite import exigir_spec_done\n\n"
        "def test_a():\n    exigir_spec_done('178')\n",
        "import pytest\n\n@pytest.fixture\ndef test_db():\n    return 1\n",
        "def test_a():\n    raise AssertionError('x')\n",
        "def test_a():\n    texto = '# assert dentro de string'\n    assert texto\n",
    ],
)
def test_verificador_aceita(fonte):
    assert _violacoes({"tests/x.py": fonte}) == []


def test_verificador_aceita_teste_importado_que_confere():
    fontes = {
        "tests/outro.py": "def test_original():\n    assert 1 == 1\n",
        "tests/x.py": (
            "from tests.outro import test_original\n"
            "from .outro import test_original as relativo\n\n"
            "def test_por_import():\n    test_original()\n\n"
            "def test_por_relativo():\n    relativo()\n"
        ),
    }
    assert _violacoes(fontes) == []


def test_verificador_nao_aceita_import_de_fora_de_tests():
    fonte = "from app.x import conferir\n\ndef test_a():\n    conferir()\n"
    assert _violacoes({"tests/x.py": fonte}) == ["tests/x.py:3 test_a sem conferência"]


def test_verificador_resiste_a_ciclo():
    fonte = "def _a():\n    _b()\n\ndef _b():\n    _a()\n\ndef test_x():\n    _a()\n"
    assert _violacoes({"tests/x.py": fonte}) == ["tests/x.py:7 test_x sem conferência"]


def test_excecao_libera_e_existe():
    fonte = "def test_a():\n    calcular()\n"
    verificador = Verificador({"tests/x.py": fonte})
    assert verificador.violacoes({"tests/x.py::test_a": "não levanta"}) == []
    assert verificador.existe("tests/x.py::test_a")
    assert not verificador.existe("tests/x.py::test_inexistente")
