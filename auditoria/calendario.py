"""Calendário de pregões da B3, só com a biblioteca padrão.

Feriados fixos nacionais em que a B3 não abre, mais os móveis calculados a
partir da Páscoa (Carnaval, Sexta-feira Santa, Corpus Christi). Se a B3 mudar o
calendário, ajuste FERIADOS_FIXOS ou EXCECOES e registre em
docs/context/dominio-b3.md.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

BRT = timezone(timedelta(hours=-3))
ABERTURA = time(10, 0)
FECHAMENTO = time(17, 0)
# Leilão de fechamento e atraso de publicação das fontes.
FIM_DA_JANELA = time(18, 15)

FERIADOS_FIXOS = {
    (1, 1),  # Confraternização Universal
    (4, 21),  # Tiradentes
    (5, 1),  # Dia do Trabalho
    (9, 7),  # Independência
    (10, 12),  # Nossa Senhora Aparecida
    (11, 2),  # Finados
    (11, 15),  # Proclamação da República
    (11, 20),  # Consciência Negra
    (12, 24),  # véspera de Natal (sem pregão)
    (12, 25),  # Natal
    (12, 31),  # último dia do ano (sem pregão)
}

# Datas avulsas: fechamentos extraordinários anunciados pela B3.
EXCECOES: set[date] = set()


def pascoa(ano: int) -> date:
    """Algoritmo de Meeus/Jones/Butcher."""
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
        p - timedelta(days=48),  # segunda de Carnaval
        p - timedelta(days=47),  # terça de Carnaval
        p - timedelta(days=2),  # Sexta-feira Santa
        p + timedelta(days=60),  # Corpus Christi
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


def ultimo_pregao_iniciado(agora: datetime) -> date:
    """Data do pregão mais recente que já abriu (em BRT)."""
    local = agora.astimezone(BRT)
    d = local.date()
    if e_pregao(d) and local.time() >= ABERTURA:
        return d
    return pregao_anterior(d)


def em_pregao(agora: datetime) -> bool:
    local = agora.astimezone(BRT)
    return e_pregao(local.date()) and ABERTURA <= local.time() <= FIM_DA_JANELA
