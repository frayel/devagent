from app.main import templates


def test_gauge_macro_rendering():
    # We load macro through a simple template string rendering.
    template = templates.env.from_string(
        '{% from "componentes.html" import gauge %}{{ gauge(75, "teste") }}'
    )
    rendered = template.render()
    assert 'class="gauge"' in rendered
    assert "teste" in rendered
    assert 'class="g-valor alta"' in rendered  # 75 > 50 gives alta
    assert "75" in rendered


def test_gauge_divergente():
    template = templates.env.from_string(
        '{% from "componentes.html" import gauge %}{{ gauge(-1.5, "Risco", -2, 2, "{:+.1f}", divergente=True) }}'
    )
    rendered = template.render()
    assert 'class="gauge"' in rendered
    assert 'class="g-valor baixa"' in rendered  # -1.5 is negative
    assert "-1.5" in rendered
