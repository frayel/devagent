"""Regressão: a página de saúde acusava tickers que o código já não pede.

Desde 09/11 o item *Yahoo Finance* listava 16 tickers sem cotação. Treze
saíram da bolsa (fusão, troca de código ou fechamento de capital) e seguiam
nas listas do código; outros três (CPLE6, ELET3, "Elet6") nem estavam mais no
código, mas a linha no banco nunca saía do alerta. Depois de 24 h a atenção
virava problema e travava o ciclo.
"""

import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.banco import _ainda_pedidos, get_simbolos_suspensos, registrar_falha_simbolo

RAIZ = Path(__file__).resolve().parent.parent

# Saíram da B3 ou trocaram de código; o Yahoo responde 404 para todos.
FORA_DA_BOLSA = {
    "ARZZ3": "AZZA3",
    "SOMA3": "AZZA3",
    "BRFS3": "MBRF3",
    "MRFG3": "MBRF3",
    "CCRO3": "MOTV3",
    "EMBR3": "EMBJ3",
    "NTCO3": "NATU3",
    "RRRP3": "BRAV3",
    "AZUL4": None,
    "CIEL3": None,
    "CRFB3": None,
    "JBSS3": None,
    "PETZ3": None,
    "CPLE6": None,
    "ELET3": "AXIA3",
}

LISTAS = [
    "app/consultor/universo.py",
    "app/collectors/highlights.py",
    "app/collectors/coesao.py",
    "app/collectors/concentracao_ordens.py",
    "app/collectors/concentracao_setorial.py",
    "app/collectors/assimetria_risco_retorno.py",
    "app/collectors/sensibilidade_juros.py",
]


def test_listas_nao_pedem_ticker_fora_da_bolsa():
    for arquivo in LISTAS:
        texto = (RAIZ / arquivo).read_text(encoding="utf-8")
        pedidos = set(re.findall(r'"([A-Z]{4}\d{1,2})"', texto))
        sobra = pedidos & FORA_DA_BOLSA.keys()
        assert not sobra, f"{arquivo} ainda pede {sorted(sobra)}"


def test_carteira_sem_repetidos():
    from app.consultor.universo import CARTEIRA_IBOVESPA

    assert len(CARTEIRA_IBOVESPA) == len(set(CARTEIRA_IBOVESPA))


def _linha(simbolo: str, ultimo: datetime) -> dict:
    return {
        "fonte": "yfinance",
        "simbolo": simbolo,
        "desde": ultimo.isoformat(),
        "ultimo_status": ultimo.isoformat(),
        "tentativas": 3,
    }


def test_ainda_pedidos_descarta_linha_parada():
    agora = datetime(2026, 11, 13, 18, 0, tzinfo=timezone.utc)
    linhas = [
        _linha("SOMA3", agora - timedelta(hours=3)),
        _linha("Elet6", agora - timedelta(days=30)),
    ]
    assert [x["simbolo"] for x in _ainda_pedidos(linhas, agora)] == ["SOMA3"]


def test_ainda_pedidos_aceita_formato_do_postgres():
    agora = datetime(2026, 11, 13, 18, 0, tzinfo=timezone.utc)
    linha = _linha("SOMA3", agora)
    linha["ultimo_status"] = "2026-11-13 17:00:00.123456+00:00"
    assert _ainda_pedidos([linha], agora) == [linha]


def test_saude_nao_acusa_ticker_que_ninguem_pede_mais():
    for _ in range(3):
        registrar_falha_simbolo("yfinance", "SOMA3")
        registrar_falha_simbolo("yfinance", "Elet6")

    velho = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    conn = sqlite3.connect(os.environ["DATABASE_PATH"])
    conn.execute(
        "UPDATE simbolos_sem_cotacao SET ultimo_status = ? WHERE simbolo = 'Elet6'",
        (velho,),
    )
    conn.commit()
    conn.close()

    assert [s["simbolo"] for s in get_simbolos_suspensos()] == ["SOMA3"]
