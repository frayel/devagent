from app.consultor.armazenamento import ler_consenso


def test_consenso_texto():
    resultado = ler_consenso("cobertura insuficiente")
    assert resultado == "cobertura insuficiente", (
        "Consenso texto não chegou inteiro à API"
    )


def test_consenso_linha_antiga():
    resultado = ler_consenso("{'compra': 3}")
    assert resultado == {"compra": 3}, "Consenso formato dict antigo falhou na leitura"


def test_consenso_json():
    resultado = ler_consenso('{"compra": 3}')
    assert resultado == {"compra": 3}, "Consenso JSON válido não virou dicionário"


def test_literal_eval_removed():
    with open("app/main.py", "r") as f:
        content = f.read()
    assert "literal_eval" not in content, (
        "literal_eval should not be present in app/main.py"
    )
