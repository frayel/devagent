from app.consultor.armazenamento import get_opinioes_historicas


def test_consultor_data_passada():
    opinions = get_opinioes_historicas("2020-01-01")
    assert isinstance(opinions, list)
