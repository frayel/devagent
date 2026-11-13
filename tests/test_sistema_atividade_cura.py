from datetime import datetime, timedelta, timezone

from app.services.sistema import PROBLEMA, verificar_atividade


def test_main_parada_declara_cura_por_entrega() -> None:
    """Issue #807: o núcleo precisa saber que este problema some com uma entrega."""
    agora = datetime(2026, 11, 13, 12, tzinfo=timezone.utc)
    main = {
        "sha": "848e3fc0000",
        "data": (agora - timedelta(days=4)).isoformat(),
        "mensagem": "feat: algo",
    }
    item = verificar_atividade({"main": main}, agora)
    assert item.nivel == PROBLEMA
    assert item.cura == "entrega"
