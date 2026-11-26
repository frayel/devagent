"""Aceite da spec 199: o radar raro que acende ganha uma linha sob a manchete.

Sem rede: a função pura recebe o histórico do exemplo; a tela lê o snapshot
`instrumentacao` gravado no banco temporário do teste, com os getters dos
radares trocados por payloads frescos e o relógio congelado em 03/12/2026.
"""

from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

import app.banco
from app.services import radares
from app.services.radares import COM_ALERTAS, RADARES, SEM_ALERTAS
from devagent.aceite import exigir_spec_done
from tests.test_aceite_150 import GETTERS, _snap, client

RAIZ = Path(__file__).resolve().parent.parent
BRT = timezone(timedelta(hours=-3))
# 03/12/2026, 11:00 BRT, pregão aberto (exemplo da spec).
AGORA = datetime(2026, 12, 3, 14, 0, tzinfo=timezone.utc)
FRESCO = datetime(2026, 12, 3, 10, 55, tzinfo=BRT)
CHAVES = [c for c, _n, _f in RADARES]

FRASE_EXAUSTAO = (
    "Exaustão de Alta acendeu: nenhum alerta nos 11 pregões registrados antes deste."
)
FRASE_FACA = "Radar de Faca Caindo acendeu: o último alerta foi há 10 pregões (18/11)."

EXCECOES = {
    date(2026, 12, 1): {"variacao_subita": 25},
    date(2026, 11, 18): {"faca_caindo": 28},
    date(2026, 12, 3): {"short_squeeze": 20},
}


def _historico(excecoes=EXCECOES, sem=()):
    pregoes = radares.janela_pregoes(AGORA)
    historico = {}
    for dia in pregoes:
        if dia < date(2026, 11, 17) or dia in sem:
            continue
        escondidos = {c: 30 for c in CHAVES}
        escondidos.update(excecoes.get(dia, {}))
        historico[dia] = {"radares_pregao": 30, "escondidos_pregao": escondidos}
    return historico


ACESOS = ("exaustao_alta", "faca_caindo", "variacao_subita")

# Um alerta com os campos que os cards dos radares do exemplo leem.
ALERTA = {
    "ticker": "PETR4",
    "variacao_hoje": 1.0,
    "retorno_acumulado": 1.0,
    "variacao": 3.5,
    "price": 30.0,
    "ratio": 2.0,
    "change_percent": 2.0,
    "dias": 4,
    "variacao_acumulada": -6.0,
    "alta_acumulada": 5.0,
    "queda_acumulada": -5.0,
    "recuperacao_intraday": 2.0,
    "queda_intraday": -2.0,
}


def _estados(acesos=ACESOS):
    return {c: (COM_ALERTAS if c in acesos else SEM_ALERTAS) for c in CHAVES}


def _anterior(historico):
    return radares.ultimo_alerta(historico, radares.janela_pregoes(AGORA)[1:])


@pytest.fixture(autouse=True)
def _spec_done():
    exigir_spec_done("199")


# --- cálculo -------------------------------------------------------------------


def test_janela_do_exemplo():
    pregoes = radares.janela_pregoes(AGORA)
    assert date(2026, 11, 20) not in pregoes
    assert pregoes[10] == date(2026, 11, 18)
    assert _anterior(_historico())["registrados"] == 11


def test_exemplo_de_ponta_a_ponta():
    raros = radares.radares_raros(_estados(), _anterior(_historico()))
    assert raros == [
        {
            "chave": "exaustao_alta",
            "nome": "Exaustão de Alta",
            "ultimo": None,
            "pregoes_atras": None,
        },
        {
            "chave": "faca_caindo",
            "nome": "Radar de Faca Caindo",
            "ultimo": date(2026, 11, 18),
            "pregoes_atras": 10,
        },
    ]
    assert radares.frases_raros(raros, 11) == [FRASE_EXAUSTAO, FRASE_FACA]


def test_com_nove_pregoes_registrados_nada_aparece():
    historico = _historico(sem=(date(2026, 11, 17), date(2026, 11, 18)))
    assert _anterior(historico)["registrados"] == 9
    assert radares.radares_raros(_estados(), _anterior(historico)) == []


def test_alerta_ha_nove_pregoes_nao_e_raro():
    excecoes = {**EXCECOES, date(2026, 11, 19): {"faca_caindo": 28}}
    del excecoes[date(2026, 11, 18)]
    raros = radares.radares_raros(_estados(), _anterior(_historico(excecoes)))
    assert [r["chave"] for r in raros] == ["exaustao_alta"]


def test_apagado_agora_nao_aparece():
    # Short Squeeze acendeu mais cedo neste pregão e está apagado agora.
    raros = radares.radares_raros(_estados(), _anterior(_historico()))
    assert "short_squeeze" not in [r["chave"] for r in raros]
    raros = radares.radares_raros(_estados(("exaustao_alta",)), _anterior(_historico()))
    assert [r["chave"] for r in raros] == ["exaustao_alta"]


def test_ordem_e_excedente():
    # Quatro acesos sem alerta anterior (só os de exceção acenderam antes).
    acesos = ("exaustao_alta", "faca_caindo", "volume_alerts", "radar_inflexao")
    raros = radares.radares_raros(_estados(acesos), _anterior(_historico()))
    assert [r["chave"] for r in raros] == [
        "volume_alerts",
        "exaustao_alta",
        "radar_inflexao",
        "faca_caindo",
    ]
    frases = radares.frases_raros(raros, 11)
    assert len(frases) == 3
    assert frases[2] == "e mais 2 radares raros acenderam; veja a aba Alertas."
    assert radares.frases_raros(raros[:3], 11)[2] == (
        "e mais 1 radar raro acendeu; veja a aba Alertas."
    )


# --- tela e snapshot -------------------------------------------------------------


@pytest.fixture
def pagina(monkeypatch):
    class Relogio(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return AGORA if tz is None else AGORA.astimezone(tz)

    monkeypatch.setattr("app.main.datetime", Relogio)
    estado = {
        chave: _snap(chave, FRESCO, [ALERTA] if chave in ACESOS else None)
        for chave in GETTERS
    }
    for chave, (modulo, funcao) in GETTERS.items():
        monkeypatch.setattr(f"{modulo}.{funcao}", lambda *a, _c=chave, **k: estado[_c])
    return estado


def _gravar(historico):
    for dia, payload in historico.items():
        app.banco.gravar_snapshot("instrumentacao", dia, "ao_vivo", "sistema", payload)


def _linhas(html: str) -> list[str]:
    m = re.search(r'<div class="span-12 manchete-container">(.*?)</div>', html, re.S)
    assert m, "manchete ausente"
    bloco = m.group(1)
    linhas = re.findall(r'<p class="manchete-raro[^"]*">(.*?)</p>', bloco, re.S)
    if linhas:
        assert bloco.index("manchete-texto") < bloco.index("manchete-raro")
    return [re.sub(r"\s+", " ", linha).strip() for linha in linhas]


def test_tela_mostra_as_duas_frases(pagina):
    _gravar(_historico())
    resp = client.get("/")
    assert resp.status_code == 200
    assert _linhas(resp.text) == [FRASE_EXAUSTAO, FRASE_FACA]


def test_tela_com_quatro_raros(pagina):
    for chave in ("volume_alerts", "radar_inflexao"):
        pagina[chave] = _snap(chave, FRESCO, [ALERTA])
    _gravar(_historico())
    linhas = _linhas(client.get("/").text)
    assert len(linhas) == 3
    assert linhas[2] == "e mais 2 radares raros acenderam; veja a aba Alertas."


def test_sem_instrumentacao_sem_linha(pagina):
    resp = client.get("/")
    assert resp.status_code == 200
    assert _linhas(resp.text) == []
    snap = client.get("/api/snapshot").json()["paineis"]["radares_ultimo_alerta"]
    assert snap["raros"] == []
    assert snap["registrados_antes"] == 0


def test_leitura_que_falha_sem_linha(pagina, monkeypatch):
    _gravar(_historico())
    original = app.banco.ler_snapshots_datas

    def falha(painel, datas):
        if painel == "instrumentacao":
            raise RuntimeError("banco fora")
        return original(painel, datas)

    monkeypatch.setattr("app.banco.ler_snapshots_datas", falha)
    resp = client.get("/")
    assert resp.status_code == 200
    assert _linhas(resp.text) == []
    snap = client.get("/api/snapshot").json()["paineis"]["radares_ultimo_alerta"]
    assert snap["raros"] == []
    assert snap["registrados_antes"] == 0


def test_data_historica_sem_linha(pagina, monkeypatch):
    _gravar(_historico())
    import app.main as main

    original = main._get_seletor_context

    def ctx(*args, **kwargs):
        return {
            **original(*args, **kwargs),
            "is_historical": True,
            "data_invalida": False,
        }

    monkeypatch.setattr("app.main._get_seletor_context", ctx)
    resp = client.get("/?data=2026-12-02")
    assert resp.status_code == 200
    assert "manchete-raro" not in resp.text
    snap = client.get("/api/snapshot?data=2026-12-02").json()
    assert snap["paineis"]["radares_ultimo_alerta"]["raros"] == []
    assert snap["paineis"]["radares_ultimo_alerta"]["registrados_antes"] == 0


def test_api_snapshot_traz_os_raros(pagina, monkeypatch):
    _gravar(_historico())
    chamadas = []
    original = app.banco.ler_snapshots_datas

    def contar(painel, datas):
        if painel == "instrumentacao":
            chamadas.append(painel)
        return original(painel, datas)

    monkeypatch.setattr("app.banco.ler_snapshots_datas", contar)
    resp = client.get("/api/snapshot").json()
    snap = resp["paineis"]["radares_ultimo_alerta"]
    assert len(chamadas) == 1
    assert snap["registrados_antes"] == 11
    assert snap["raros"] == [
        {
            "chave": "exaustao_alta",
            "nome": "Exaustão de Alta",
            "ultimo": None,
            "pregoes_atras": None,
        },
        {
            "chave": "faca_caindo",
            "nome": "Radar de Faca Caindo",
            "ultimo": "2026-11-18",
            "pregoes_atras": 10,
        },
    ]
    # Invariantes de produção da spec.
    for item in snap["raros"]:
        assert item["chave"] in CHAVES
        assert item["pregoes_atras"] is None or 10 <= item["pregoes_atras"] < 20
        painel = resp["paineis"].get(item["chave"])
        if isinstance(painel, dict) and "alertas" in painel:
            assert painel["alertas"]
    html = client.get("/").text
    assert len(chamadas) == 2  # uma leitura por requisição
    assert len(_linhas(html)) == min(len(snap["raros"]), 2) + (
        1 if len(snap["raros"]) > 2 else 0
    )


def test_390px_sem_rolagem_horizontal(pagina):
    from playwright.sync_api import sync_playwright

    _gravar(_historico())
    html = client.get("/").text
    css = (RAIZ / "app" / "static" / "tema.css").read_text(encoding="utf-8")
    html = re.sub(r"<script\b[^>]*\bsrc=[^>]*>\s*</script>", "", html)
    html = re.sub(r'<link rel="stylesheet"[^>]*>', f"<style>{css}</style>", html)
    html = re.sub(r'<meta http-equiv="refresh"[^>]*>', "", html)
    with sync_playwright() as p:
        navegador = p.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH") or None
        )
        try:
            aba = navegador.new_page(viewport={"width": 390, "height": 844})
            aba.route("**/*", lambda rota: rota.abort())
            aba.set_content(html)
            medida = aba.evaluate(
                """() => {
                  const linhas = [...document.querySelectorAll('p.manchete-raro')];
                  return {
                    scroll: document.documentElement.scrollWidth,
                    largura: window.innerWidth,
                    linhas: linhas.length,
                    direita: Math.max(...linhas.map(l => l.getBoundingClientRect().right)),
                  };
                }"""
            )
        finally:
            navegador.close()
    assert medida["linhas"] == 2, medida
    assert medida["scroll"] <= medida["largura"], medida
    assert medida["direita"] <= medida["largura"], medida
