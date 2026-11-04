from datetime import datetime, timezone, timedelta
from app.agendador import intervalo


def test_intervalo_feriado():
    BRT = timezone(timedelta(hours=-3))

    # 02/11/2026 às 11h BRT - Feriado
    d1 = datetime(2026, 11, 2, 11, 0, tzinfo=BRT)
    assert intervalo(d1) == timedelta(hours=2)

    # 28/10/2026 às 11h BRT - Dia útil
    d2 = datetime(2026, 10, 28, 11, 0, tzinfo=BRT)
    assert intervalo(d2) == timedelta(minutes=15)
