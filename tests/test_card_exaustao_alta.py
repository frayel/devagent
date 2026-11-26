"""Regressão: o card Exaustão de Alta mostra o ativo e a variação.

O template montava as células com a chave `texto`, que `tabela_ativos` não lê
(ela lê `conteudo`): com o radar aceso, a tabela saía com as linhas vazias.
"""

from __future__ import annotations

import re

from tests.test_aceite_150 import _snap, client
from tests.test_aceite_199 import ALERTA, FRESCO, pagina  # noqa: F401


def test_card_mostra_ticker_e_variacao(pagina):  # noqa: F811
    pagina["exaustao_alta"] = _snap(
        "exaustao_alta", FRESCO, [{**ALERTA, "ticker": "WEGE3", "variacao": 3.5}]
    )
    html = client.get("/").text
    m = re.search(r'<tbody data-rank="exaustao_alta">(.*?)</tbody>', html, re.S)
    assert m, "tabela da Exaustão de Alta ausente"
    texto = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1)))
    assert "WEGE3" in texto
    assert "▲ 3,50%" in texto
