from app import calendario
import auditoria.calendario as auditoria_calendario
from datetime import datetime


def test_feriados_com_auditoria():
    ano = datetime.now().year
    assert calendario.feriados(ano) == auditoria_calendario.feriados(ano)
    assert calendario.feriados(ano + 1) == auditoria_calendario.feriados(ano + 1)


def test_pregao_corrente_fim_de_semana():
    # 2026-10-31 is Saturday, should return Friday 2026-10-30
    agora = datetime.fromisoformat("2026-10-31T02:07:01.846918+00:00")
    assert calendario.pregao_corrente(agora).isoformat() == "2026-10-30"
