import ast
import re
from pathlib import Path


PERMITIDOS = {"clima_global.py", "mt5.py"}


def analisar_arquivo_coletor(conteudo: str, nome_arquivo: str) -> list[str]:
    """Analisa o código-fonte de um coletor para garantir a invariante da Spec 135:

    Se o arquivo lê `chartPreviousClose`, só pode consultar range=1d (exceto clima_global.py e mt5.py).
    """
    if nome_arquivo in PERMITIDOS:
        return []

    # Se chartPreviousClose não aparece como chave de acesso ou atributo no código
    # (ignora comentários se parsed via AST, ou busca string "chartPreviousClose")
    tem_leitura_chart_previous_close = False
    try:
        tree = ast.parse(conteudo, filename=nome_arquivo)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value == "chartPreviousClose":
                tem_leitura_chart_previous_close = True
                break
            elif isinstance(node, ast.Attribute) and node.attr == "chartPreviousClose":
                tem_leitura_chart_previous_close = True
                break
    except Exception:
        # Fallback para regex
        if re.search(r'["\']chartPreviousClose["\']', conteudo):
            tem_leitura_chart_previous_close = True

    if not tem_leitura_chart_previous_close:
        return []

    # Se lê chartPreviousClose, verifica se há consulta com range != 1d
    erros = []
    # Procura por range=<algo> em strings ou URLs
    matches = re.findall(r"range=([a-zA-Z0-9_]+)", conteudo)
    for r in matches:
        if r != "1d":
            erros.append(
                f"{nome_arquivo} lê 'chartPreviousClose' mas consulta range={r}. "
                "Conforme Spec 135 (docs/specs/135-acoes-variacao-do-dia-sem-janela-de-15-dias.md), "
                "`chartPreviousClose` com range maior que 1d reflete o fechamento anterior à primeira "
                "barra da janela histórica e não o pregão anterior. Use a função compartilhada "
                "`fechamento_anterior` em app/collectors/utils.py."
            )

    return erros


def test_fronteira_chart_previous_close_coletores_reais():
    """Varre todos os coletores em app/collectors/*.py e verifica que nenhum viola a Spec 135."""
    collectors_dir = Path("app/collectors")
    arquivos_py = list(collectors_dir.glob("*.py"))
    assert len(arquivos_py) > 0, "Nenhum coletor encontrado em app/collectors/"

    todos_erros = []
    for caminho in arquivos_py:
        conteudo = caminho.read_text(encoding="utf-8")
        erros = analisar_arquivo_coletor(conteudo, caminho.name)
        todos_erros.extend(erros)

    assert not todos_erros, "\n".join(todos_erros)


def test_fronteira_chart_previous_close_falha_em_coletor_invalido():
    """Critério Spec 135: falha num coletor de exemplo, escrito no próprio teste, que lê chartPreviousClose com range=15d."""
    coletor_exemplo = """
import httpx

def coletar_dados():
    url = "https://query1.finance.yahoo.com/v8/finance/spark?symbols=PETR4.SA&range=15d&interval=1d"
    resp = httpx.get(url).json()
    meta = resp["spark"]["result"][0]["response"][0]["meta"]
    fechamento_anterior = meta["chartPreviousClose"]
    return fechamento_anterior
"""
    erros = analisar_arquivo_coletor(coletor_exemplo, "coletor_exemplo_ficticio.py")
    assert len(erros) > 0, (
        "O teste de fronteira deveria falhar no coletor de exemplo com range=15d"
    )
    assert "Spec 135" in erros[0]
    assert "range=15d" in erros[0]
    assert "fechamento_anterior" in erros[0]
