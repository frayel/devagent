import re
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_rodape_horarios_completos():
    response = client.get("/")
    assert response.status_code == 200
    html = response.text

    # Encontra todos os rodapés
    rodapes = re.findall(r'<div class="rodape">Fonte (.*?)</div>', html)

    # Verifica se os rodapés seguem o formato de data completo (dd/mm/aaaa) ou apenas horário
    # Alguns rodapés podem ser apenas de horário, mas se tiverem data, deve ter o ano.
    for rodape in rodapes:
        if "BRT" in rodape:
            # Pega a parte da data/hora (depois do · )
            partes = rodape.split("·")
            if len(partes) > 1:
                data_hora_str = partes[-1].strip()
                # Verifica se não tem um formato incompleto como dd/mm HH:MM
                # Se tem barra, deve ter duas barras para representar o ano
                if "/" in data_hora_str:
                    assert data_hora_str.count("/") == 2, (
                        f"Data incompleta encontrada no rodapé: {rodape}"
                    )
