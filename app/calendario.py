"""Calendário de pregões da B3, com os feriados em BRT.
Baseado no auditoria/calendario.py.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

BRT = timezone(timedelta(hours=-3))
ABERTURA = time(10, 0)
FECHAMENTO = time(17, 0)
FIM_DA_JANELA = time(18, 15)

FERIADOS_FIXOS = {
    (1, 1),
    (4, 21),
    (5, 1),
    (9, 7),
    (10, 12),
    (11, 2),
    (11, 15),
    (11, 20),
    (12, 24),
    (12, 25),
    (12, 31),
}
EXCECOES: set[date] = set()


def pascoa(ano: int) -> date:
    a = ano % 19
    b, c = divmod(ano, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    ll = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ll) // 451
    mes = (h + ll - 7 * m + 114) // 31
    dia = (h + ll - 7 * m + 114) % 31 + 1
    return date(ano, mes, dia)


def feriados(ano: int) -> set[date]:
    p = pascoa(ano)
    moveis = {
        p - timedelta(days=48),
        p - timedelta(days=47),
        p - timedelta(days=2),
        p + timedelta(days=60),
    }
    fixos = {date(ano, m, d) for m, d in FERIADOS_FIXOS}
    return fixos | moveis | {d for d in EXCECOES if d.year == ano}


def e_pregao(d: date) -> bool:
    return d.weekday() < 5 and d not in feriados(d.year)


def pregao_anterior(d: date) -> date:
    d -= timedelta(days=1)
    while not e_pregao(d):
        d -= timedelta(days=1)
    return d


def mercado_aberto(agora: datetime) -> bool:
    local = agora.astimezone(BRT)
    d = local.date()
    return e_pregao(d) and ABERTURA <= local.time() <= FIM_DA_JANELA


def pregao_corrente(agora: datetime) -> date:
    local = agora.astimezone(BRT)
    d = local.date()
    if e_pregao(d) and local.time() >= time(0, 0):
        # We consider the day as the current pregao even before opening (pre-abertura)
        # However, before midnight it would be the same day anyway.
        return d
    return ultimo_pregao_fechado(agora)


def ultimo_pregao_fechado(agora: datetime) -> date:
    local = agora.astimezone(BRT)
    d = local.date()
    # Se for dia de pregão e já passou das 18h15, o pregão de hoje já fechou
    if e_pregao(d) and local.time() > FIM_DA_JANELA:
        return d
    # Caso contrário, é o pregão anterior
    return pregao_anterior(d)


def proximos_pregoes(agora: datetime, n: int) -> list[date]:
    local = agora.astimezone(BRT)
    d = local.date()
    # If today is pregao and it hasn't ended yet, today is the first next pregao.
    # Otherwise we start looking from tomorrow.
    if e_pregao(d) and local.time() <= FIM_DA_JANELA:
        pass
    else:
        d += timedelta(days=1)

    result: list[date] = []
    while len(result) < n:
        if e_pregao(d):
            result.append(d)
        d += timedelta(days=1)
    return result
