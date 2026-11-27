"""Checagens do Consultor e do /sistema (incidente de 17/11 a 27/11/2026)."""

from datetime import datetime, timezone

from auditoria.auditar import (
    AVISO,
    FALHA,
    OK,
    Resultado,
    checar_consultor,
    checar_sistema,
)

AGORA = datetime(2026, 11, 27, 16, 33, tzinfo=timezone.utc)  # sexta, 13h33 BRT


def _por_id(resultados):
    return {r.id: r for r in resultados}


def test_consultor_vazio_de_27_11_seria_detectado():
    """O que o /api/consultor devolvia em produção em 27/11/2026."""
    dados = {
        "ativos_avaliados": 0,
        "informacoes_de": {"sinais_coletado_em": "17/11/2026 21:02"},
    }
    r = _por_id(checar_consultor(dados, AGORA))
    assert r["consultor.avaliados"].status == FALHA
    assert r["consultor.frescor"].status == FALHA


def test_consultor_saudavel_passa():
    dados = {
        "ativos_avaliados": 87,
        "informacoes_de": {"sinais_coletado_em": "26/11/2026 18:40"},
    }
    r = _por_id(checar_consultor(dados, AGORA))
    assert r["consultor.avaliados"].status == OK
    assert r["consultor.frescor"].status == OK


def test_consultor_sem_data_reprova():
    r = _por_id(checar_consultor({"ativos_avaliados": 87}, AGORA))
    assert r["consultor.frescor"].status == FALHA


def test_sistema_verde_com_auditoria_vermelha_reprova():
    achados = [Resultado("consultor.avaliados", FALHA, "O Consultor avaliou")]
    dados = {"geral": {"nivel": "ok", "pendentes": []}}
    r = _por_id(checar_sistema(dados, achados))
    assert r["sistema.contrato"].status == OK
    assert r["sistema.coerencia"].status == FALHA
    assert "consultor.avaliados" in r["sistema.coerencia"].detalhe


def test_sistema_que_acusa_fica_coerente_e_vira_aviso():
    achados = [Resultado("consultor.avaliados", FALHA, "O Consultor avaliou")]
    dados = {
        "geral": {
            "nivel": "problema",
            "pendentes": [
                {
                    "nivel": "problema",
                    "grupo": "Coleta",
                    "nome": "Séries do Consultor",
                    "resumo": "6 pregões sem renovar",
                }
            ],
        }
    }
    r = _por_id(checar_sistema(dados, achados))
    assert r["sistema.coerencia"].status == OK
    assert r["sistema.problemas"].status == AVISO
    assert "Séries do Consultor" in r["sistema.problemas"].detalhe


def test_sistema_fora_do_contrato_reprova():
    r = _por_id(checar_sistema({"grupos": []}, []))
    assert r["sistema.contrato"].status == FALHA


def test_atencao_sem_relacao_nao_basta():
    """27/11/2026: /sistema em atenção por agendamentos perdidos, Consultor vazio."""
    achados = [Resultado("consultor.avaliados", FALHA, "O Consultor avaliou")]
    dados = {
        "geral": {
            "nivel": "atencao",
            "pendentes": [
                {"nivel": "atencao", "grupo": "Workflows", "nome": "Auditoria"}
            ],
        }
    }
    r = _por_id(checar_sistema(dados, achados))
    assert r["sistema.coerencia"].status == FALHA


def test_sem_falhas_na_auditoria_e_coerente():
    r = _por_id(checar_sistema({"geral": {"nivel": "ok", "pendentes": []}}, []))
    assert r["sistema.coerencia"].status == OK
