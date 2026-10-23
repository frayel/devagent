from app import calendario
import auditoria.calendario as auditoria_calendario
from datetime import datetime


def test_feriados_com_auditoria():
    ano = datetime.now().year
    assert calendario.feriados(ano) == auditoria_calendario.feriados(ano)
    assert calendario.feriados(ano + 1) == auditoria_calendario.feriados(ano + 1)
