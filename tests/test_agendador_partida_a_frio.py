"""Partida a frio dos coletores de janela própria (#919).

`consultor_historico`, `consultor_fechamento`, `consultor_yahoo` e
`clima_global` não gravam snapshot com o nome do módulo. A partida a frio
deles olha a instrumentação das rodadas (quem rodou em cada dia), não
`ler_snapshot(nome)`, senão rodam em toda rodada, fora da janela.
"""

from __future__ import annotations

import importlib
from datetime import date, datetime, timezone

import app.banco
import app.consultor.avaliador_historico as avaliador_historico
import app.database
from app import agendador

PROPRIOS = (
    "clima_global",
    "consultor_historico",
    "consultor_fechamento",
    "consultor_yahoo",
)

# Segunda, 16/11/2026, 18h00 BRT: a rodada que a issue mostra.
SEGUNDA_18H = datetime(2026, 11, 16, 21, 0, 45, tzinfo=timezone.utc)
# Segunda, 16/11/2026, 21h00 BRT: depois de todas as janelas do dia.
SEGUNDA_21H = datetime(2026, 11, 17, 0, 0, tzinfo=timezone.utc)
# Sábado, 14/11/2026, 10h00 BRT.
SABADO_10H = datetime(2026, 11, 14, 13, 0, tzinfo=timezone.utc)

SEXTA = date(2026, 11, 13)
SABADO = date(2026, 11, 14)
SEGUNDA = date(2026, 11, 16)


def _relogio(instante: datetime) -> type[datetime]:
    class _Relogio(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return instante if tz is None else instante.astimezone(tz)

    return _Relogio


def _execucoes(execucoes: dict[date, list[str]]) -> None:
    for dia, nomes in execucoes.items():
        app.banco.gravar_snapshot(
            "instrumentacao",
            dia,
            "final",
            "teste",
            {"tempos": {n: 1.0 for n in nomes}, "vazias": {}, "rodadas": {}},
        )


def _rodar(monkeypatch, instante: datetime, instrumentar: bool = False) -> list[str]:
    """Roda `_coletar` no instante, com todo painel presente menos os de janela
    própria, e devolve os coletores chamados."""
    chamadas: list[str] = []
    ler_real = app.banco.ler_snapshot
    gravar_real = app.banco.gravar_snapshot

    def gravar(painel, *a, **k):
        if painel == "instrumentacao":
            gravar_real(painel, *a, **k)

    def ler(painel, data_referencia=None):
        if painel == "instrumentacao":
            return ler_real(painel, data_referencia)
        if painel in PROPRIOS:
            return None
        return {"estado_snapshot": "final", "estado": "final"}

    def importar(caminho):
        nome = caminho.rsplit(".", 1)[-1]

        class _Coletor:
            @staticmethod
            def collect_and_save():
                chamadas.append(nome)
                return True

        return _Coletor

    monkeypatch.setattr(avaliador_historico, "rodar_backtest", lambda: None)
    monkeypatch.setattr(app.banco, "ler_snapshot", ler)
    monkeypatch.setattr(app.banco, "gravar_snapshot", gravar)
    monkeypatch.setattr(importlib, "import_module", importar)
    monkeypatch.setattr(agendador, "datetime", _relogio(instante))
    monkeypatch.setattr(agendador, "_avisar_falha", lambda *a, **k: None)
    monkeypatch.setattr(agendador, "_registrar_erro", lambda *a, **k: None)
    if not instrumentar:
        monkeypatch.setattr(
            app.database, "gravar_instrumentacao_rodada", lambda *a, **k: None
        )
    agendador._coletar([])
    return chamadas


def test_segunda_18h_nao_roda_o_historico_que_rodou_no_sabado(monkeypatch):
    _execucoes(
        {
            SEXTA: ["clima_global", "consultor_fechamento", "consultor_yahoo"],
            SABADO: ["consultor_historico"],
        }
    )
    chamadas = _rodar(monkeypatch, SEGUNDA_18H)
    assert "consultor_historico" not in chamadas
    # O fechamento só abre depois das 18h15, e o último pregão fechado é a sexta.
    assert "consultor_fechamento" not in chamadas
    assert "consultor_yahoo" not in chamadas
    # O clima global está na própria janela (7h às 18h15) e os do pregão seguem iguais.
    assert "clima_global" in chamadas
    assert "ibovespa" in chamadas


def test_sabado_roda_o_historico(monkeypatch):
    _execucoes({SABADO: ["consultor_historico"]})
    assert "consultor_historico" in _rodar(monkeypatch, SABADO_10H)


def test_sem_execucao_registrada_e_partida_a_frio(monkeypatch):
    chamadas = _rodar(monkeypatch, SEGUNDA_18H)
    for nome in PROPRIOS:
        assert nome in chamadas


def test_historico_de_mais_de_uma_semana_e_partida_a_frio(monkeypatch):
    _execucoes({date(2026, 11, 7): ["consultor_historico"]})
    assert "consultor_historico" in _rodar(monkeypatch, SEGUNDA_18H)


def test_fechamento_que_nao_rodou_no_ultimo_pregao_e_partida_a_frio(monkeypatch):
    # Rodou na quinta, mas não na sexta (o último pregão fechado às 18h00 de segunda).
    _execucoes({date(2026, 11, 12): ["consultor_fechamento", "consultor_yahoo"]})
    chamadas = _rodar(monkeypatch, SEGUNDA_18H)
    assert "consultor_fechamento" in chamadas
    assert "consultor_yahoo" in chamadas


def test_segunda_21h_nao_roda_o_que_rodou_na_segunda(monkeypatch):
    _execucoes(
        {
            SEGUNDA: ["clima_global", "consultor_fechamento", "consultor_yahoo"],
            SABADO: ["consultor_historico"],
        }
    )
    chamadas = _rodar(monkeypatch, SEGUNDA_21H)
    for nome in PROPRIOS:
        assert nome not in chamadas


def test_a_rodada_do_sabado_basta_para_a_de_segunda(monkeypatch):
    """Ponta a ponta: a instrumentação gravada no sábado segura a segunda."""
    assert "consultor_historico" in _rodar(monkeypatch, SABADO_10H, instrumentar=True)
    payload = app.banco.ler_snapshot("instrumentacao", SABADO)
    assert "consultor_historico" in payload["tempos"]
    assert "consultor_historico" not in _rodar(monkeypatch, SEGUNDA_18H)


def test_falha_ao_ler_execucoes_volta_a_partida_a_frio(monkeypatch):
    def quebra(*a, **k):
        raise RuntimeError("banco fora")

    monkeypatch.setattr(app.banco, "ler_snapshots_datas", quebra)
    assert agendador._execucoes_recentes(SEGUNDA) == {}
