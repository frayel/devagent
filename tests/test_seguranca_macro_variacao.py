import pytest
from jinja2 import Environment, FileSystemLoader


@pytest.fixture
def env():
    return Environment(loader=FileSystemLoader("app/templates"), autoescape=True)


def test_macro_variacao_com_valor_nao_confiavel(env):
    template = env.from_string("""
        {% from "componentes.html" import variacao %}
        {{ variacao(valor | e, sinal) | safe }}
    """)
    html = template.render(valor="<script>alert(1)</script>", sinal=1)

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
