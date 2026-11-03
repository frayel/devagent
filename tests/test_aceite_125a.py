from datetime import datetime, timedelta, timezone


def test_intervalo_tentativa_fechamento():
    from app.agendador import intervalo

    BRT = timezone(timedelta(hours=-3))
    # 18h40 BRT num dia de pregão (2023-01-02, segunda-feira, não é feriado)
    agora_30min = datetime(2023, 1, 2, 18, 40, tzinfo=BRT)
    assert intervalo(agora_30min) == timedelta(minutes=30)

    # 20h10 BRT no mesmo dia
    agora_2h = datetime(2023, 1, 2, 20, 10, tzinfo=BRT)
    assert intervalo(agora_2h) == timedelta(hours=2)
