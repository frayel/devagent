"""Leitor mínimo de expressões cron de 5 campos (spec 082).

Serve para a página de sistema saber quando um workflow agendado do GitHub
deveria ter rodado e comparar com quando ele rodou de fato. Entende `*`,
números, listas, intervalos e passos (`*/5`, `13-21`, `1-5`, `7,37`), em UTC,
como o GitHub Actions. Sem dependência nova.
"""

from __future__ import annotations

from datetime import datetime, timedelta

LIMITES = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 7))


def _campo(texto: str, minimo: int, maximo: int) -> set[int]:
    valores: set[int] = set()
    for parte in texto.split(","):
        passo = 1
        if "/" in parte:
            parte, p = parte.split("/", 1)
            passo = int(p)
        if parte == "*":
            ini, fim = minimo, maximo
        elif "-" in parte:
            a, b = parte.split("-", 1)
            ini, fim = int(a), int(b)
        else:
            ini = int(parte)
            fim = maximo if passo > 1 else ini
        if ini < minimo or fim > maximo or ini > fim or passo < 1:
            raise ValueError(f"campo cron inválido: {texto}")
        valores.update(range(ini, fim + 1, passo))
    return valores


class Cron:
    def __init__(self, expressao: str) -> None:
        partes = expressao.split()
        if len(partes) != 5:
            raise ValueError(f"cron precisa de 5 campos: {expressao!r}")
        self.expressao = expressao
        campos = [_campo(t, *lim) for t, lim in zip(partes, LIMITES)]
        self.minutos, self.horas, self.dias, self.meses, dias_semana = campos
        # 0 e 7 são domingo; Python numera segunda = 0.
        self.dias_semana = {(d - 1) % 7 for d in dias_semana}
        self._dia_restrito = partes[2] != "*"
        self._semana_restrita = partes[4] != "*"

    def casa(self, t: datetime) -> bool:
        if t.minute not in self.minutos or t.hour not in self.horas:
            return False
        if t.month not in self.meses:
            return False
        no_dia = t.day in self.dias
        na_semana = t.weekday() in self.dias_semana
        if self._dia_restrito and self._semana_restrita:
            return no_dia or na_semana
        return no_dia and na_semana

    def disparos(self, inicio: datetime, fim: datetime) -> list[datetime]:
        """Horários em que o cron dispara no intervalo (inicio, fim]."""
        t = inicio.replace(second=0, microsecond=0) + timedelta(minutes=1)
        saida: list[datetime] = []
        while t <= fim:
            if self.casa(t):
                saida.append(t)
            t += timedelta(minutes=1)
        return saida
