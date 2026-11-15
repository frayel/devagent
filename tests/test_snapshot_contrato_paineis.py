"""Regressão da issue #872: todo painel do /api/snapshot cumpre o contrato.

A auditoria (`api.contrato_chaves`) exige `fonte` e `coletado_em` em todo
painel que é objeto. O `confluencia_radares` da spec 155 chegou à produção
sem os dois campos.
"""

from auditoria.auditar import OK, checar_contrato_snapshot
from tests.test_aceite_155 import _exemplo, client, radares  # noqa: F401


def test_snapshot_cumpre_o_contrato_de_chaves(radares):  # noqa: F811
    _exemplo(radares)
    snapshot = client.get("/api/snapshot").json()
    [resultado] = checar_contrato_snapshot(snapshot)
    assert resultado.status == OK, resultado.detalhe


def test_confluencia_publica_fonte_e_coletado_em(radares):  # noqa: F811
    painel = client.get("/api/snapshot").json()["paineis"]["confluencia_radares"]
    assert painel["fonte"] == "composto"
    assert painel["coletado_em"]
