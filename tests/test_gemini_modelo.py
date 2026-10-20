from datetime import datetime, timedelta, timezone

import httpx

from app.collectors import registro_fontes
from app.services import gemini_modelo, consultor_opinioes

GERA = ["generateContent"]


def _m(nome, metodos=GERA):
    return {"name": f"models/{nome}", "supportedGenerationMethods": metodos}


def test_escolhe_flash_lite_estavel_mais_novo():
    modelos = [
        _m("gemini-2.5-flash-lite"),
        _m("gemini-3.10-flash-lite"),
        _m("gemini-3.9-flash-lite"),
        _m("gemini-4-flash-lite-preview-09-2026"),
        _m("gemini-flash-lite-latest"),
        _m("gemini-5-flash-lite-exp"),
        _m("gemini-4-flash"),
        _m("gemini-9-flash-lite", ["embedContent"]),
    ]
    assert gemini_modelo.escolher(modelos) == "gemini-3.10-flash-lite"


def test_escolha_ignora_recusados_e_lista_vazia():
    modelos = [_m("gemini-3.5-flash-lite"), _m("gemini-3.1-flash-lite")]
    assert (
        gemini_modelo.escolher(modelos, {"gemini-3.5-flash-lite"})
        == "gemini-3.1-flash-lite"
    )
    assert gemini_modelo.escolher([_m("gemini-4-flash")]) is None


def test_descoberta_fica_em_cache_por_24h(monkeypatch):
    chamadas = []

    def listar(api_key):
        chamadas.append(api_key)
        return [_m("gemini-3.5-flash-lite")]

    monkeypatch.setattr(gemini_modelo, "_listar_modelos", listar)
    t0 = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
    assert gemini_modelo.modelo_atual("k", t0) == "gemini-3.5-flash-lite"
    gemini_modelo.modelo_atual("k", t0 + timedelta(hours=23))
    assert len(chamadas) == 1
    gemini_modelo.modelo_atual("k", t0 + timedelta(hours=25))
    assert len(chamadas) == 2
    assert gemini_modelo.descricao() == "gemini-3.5-flash-lite (descoberto)"


def test_variavel_manual_tem_prioridade(monkeypatch):
    monkeypatch.setenv("GEMINI_MODELO", "gemini-x")
    assert gemini_modelo.modelo_atual("k") == "gemini-x"
    assert gemini_modelo.descartar("gemini-x") is False
    assert gemini_modelo.descricao() == "gemini-x (manual)"


def test_listagem_falha_usa_ultimo_que_funcionou(monkeypatch):
    assert gemini_modelo.modelo_atual("k") == "gemini-3.5-flash-lite"

    def quebra(api_key):
        raise httpx.ConnectError("sem rede")

    monkeypatch.setattr(gemini_modelo, "_listar_modelos", quebra)
    assert gemini_modelo.modelo_atual("k", forcar=True) == "gemini-3.5-flash-lite"


def test_listagem_falha_sem_historico_usa_reserva(monkeypatch):
    def quebra(api_key):
        raise httpx.ConnectError("sem rede")

    monkeypatch.setattr(gemini_modelo, "_listar_modelos", quebra)
    assert gemini_modelo.modelo_atual("k") == gemini_modelo.RESERVA[0]
    gemini_modelo.descartar(gemini_modelo.RESERVA[0])
    assert gemini_modelo.modelo_atual("k") == gemini_modelo.RESERVA[1]
    assert gemini_modelo.descricao().endswith("(reserva)")


class _Resp:
    def __init__(self, status, corpo=None):
        self.status_code = status
        self._corpo = corpo or {}

    def json(self):
        return self._corpo


def test_404_descarta_modelo_e_tenta_o_proximo(monkeypatch):
    monkeypatch.setattr(
        gemini_modelo,
        "_listar_modelos",
        lambda k: [_m("gemini-3.5-flash-lite"), _m("gemini-3.1-flash-lite")],
    )
    urls = []

    def post(url, **kw):
        urls.append(url)
        return _Resp(404) if "3.5" in url else _Resp(200)

    monkeypatch.setattr(httpx, "post", post)
    registro_fontes.limpar()
    resp = consultor_opinioes._gerar("k", {})
    assert resp.status_code == 200
    assert "gemini-3.5-flash-lite" in urls[0]
    assert "gemini-3.1-flash-lite" in urls[1]
    fonte = registro_fontes.fontes()["Gemini"]
    assert fonte.recentes[-2:] == [False, True]
    assert fonte.graves[-2] is False  # 404 é pedido errado, não fonte fora do ar


def test_geracao_registra_chave_recusada_como_grave(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda url, **kw: _Resp(403))
    registro_fontes.limpar()
    resp = consultor_opinioes._gerar("k", {})
    assert resp.status_code == 403
    fonte = registro_fontes.fontes()["Gemini"]
    assert fonte.recentes[-1] is False and fonte.graves[-1] is True


def test_pagina_de_sistema_mostra_modelo():
    from app.services.sistema import verificar_integracoes

    itens = verificar_integracoes(
        {},
        None,
        {"GEMINI_API_KEY": "k"},
        datetime.now(timezone.utc),
        "gemini-3.5-flash-lite (descoberto)",
    )
    gemini = next(i for i in itens if i.nome == "Gemini")
    assert "gemini-3.5-flash-lite (descoberto)" in gemini.detalhe
