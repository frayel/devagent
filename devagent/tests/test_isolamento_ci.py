import os

from devagent.conferir_pr import titulo_do_pr


def test_testes_nao_enxergam_o_evento_real_do_pr() -> None:
    assert "GITHUB_EVENT_PATH" not in os.environ
    assert "GITHUB_EVENT_NAME" not in os.environ
    assert titulo_do_pr() == ""
