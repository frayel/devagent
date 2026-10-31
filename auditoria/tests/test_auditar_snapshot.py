from auditoria.auditar import checar_contrato_snapshot, FALHA, OK


def test_checar_contrato_snapshot_valido():
    snapshot = {
        "paineis": {
            "ibov": {"fonte": "b3", "coletado_em": "2026-10-30"},
            "outro": [1, 2, 3],
        }
    }
    r = checar_contrato_snapshot(snapshot)
    assert len(r) == 1
    assert r[0].status == OK


def test_checar_contrato_snapshot_invalido():
    snapshot = {
        "paineis": {
            "ibov": {"fonte": "b3"},
            "dolar": {"coletado_em": "2026-10-30"},
            "juros": {"valor": 10},
        }
    }
    r = checar_contrato_snapshot(snapshot)
    assert len(r) == 1
    assert r[0].status == FALHA
    assert "'ibov' não possui 'coletado_em'" in r[0].detalhe
    assert "'dolar' não possui 'fonte'" in r[0].detalhe
    assert "'juros' não possui 'fonte'" in r[0].detalhe
