from pathlib import Path


def test_render_yaml_variables():
    content = Path("render.yaml").read_text()

    # Variáveis que o render.yaml declara sem valor
    assert "- key: GEMINI_API_KEY\n        sync: false" in content
    assert "- key: DATABASE_URL\n        sync: false" in content

    # Variáveis que não devem estar no render.yaml
    assert "GEMINI_MODELO" not in content
    assert "BRAPI_TOKEN" not in content
    assert "GEMINI_MAX_CHAMADAS_DIA" not in content
