from datetime import datetime, timezone
from app.consultor.sintese import calcular_consenso, obter_decisao_final


def test_calcular_consenso_insuficiente():
    res = calcular_consenso(
        [
            {
                "casa": "XP",
                "recomendacao": "compra",
                "preco_alvo": 10.0,
                "data_materia": datetime.now(timezone.utc).isoformat(),
            }
        ]
    )
    assert res["consenso"] == "cobertura insuficiente"


def test_calcular_consenso_valido():
    dt = datetime.now(timezone.utc).isoformat()
    ops = [
        {
            "casa": "XP",
            "recomendacao": "compra",
            "preco_alvo": 10.0,
            "data_materia": dt,
        },
        {
            "casa": "BTG",
            "recomendacao": "compra",
            "preco_alvo": 12.0,
            "data_materia": dt,
        },
        {
            "casa": "Itau",
            "recomendacao": "venda",
            "preco_alvo": 8.0,
            "data_materia": dt,
        },
    ]
    res = calcular_consenso(ops)
    assert res["consenso"] == "dividido"
    assert res["preco_alvo_mediano"] == 10.0
    assert res["faixa"] == (8.0, 12.0)


def test_obter_decisao_final_comprar_venda():
    aval = {"decisao": "Comprar", "regra": "R5", "gatilho": "invalida", "mm200": 8.0}
    consenso = {"consenso": "venda", "detalhes": {}}
    dec, frase, gatilho = obter_decisao_final(aval, consenso, 10.0, 9.0)
    assert dec == "Aguardar"
    assert "recomenda venda" in frase


def test_obter_decisao_final_vender_compra():
    aval = {"decisao": "Vender", "regra": "R2", "gatilho": "invalida", "mm200": 11.0}
    consenso = {"consenso": "compra", "detalhes": {}}
    dec, frase, gatilho = obter_decisao_final(aval, consenso, 10.0, 9.0)
    assert dec == "Aguardar"
    assert "recomenda compra" in frase
    assert "11.00" in gatilho


def test_obter_decisao_final_no_radar():
    aval = {"decisao": "Sem sinal", "regra": "R0", "gatilho": "-"}
    consenso = {"consenso": "compra", "potencial": 0.20, "detalhes": {"total": 3}}
    dec, frase, gatilho = obter_decisao_final(aval, consenso, 10.0, 11.0)
    assert dec == "No radar"
    assert "compra com potencial" in frase
    assert "11.00" in gatilho
