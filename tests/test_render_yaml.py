from pathlib import Path


def test_render_yaml_variables():
    content = Path("render.yaml").read_text()

    # Assert variables required by spec 092a exist
    assert "- key: GEMINI_API_KEY\n        sync: false" in content
    assert "- key: BRAPI_TOKEN\n        sync: false" in content
    assert "- key: DATABASE_URL\n        sync: false" in content

    # Assert variables NOT required by spec 092a are absent
    assert "GEMINI_MODELO" not in content
    assert "GEMINI_MAX_CHAMADAS_DIA" not in content
