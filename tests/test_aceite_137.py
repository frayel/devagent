from datetime import datetime, timezone
import pytest

from devagent.aceite import exigir_spec_done
from auditoria import auditar
from auditoria.auditar import (
    obter_referencia,
    checar_referencia,
    Painel,
    Referencia,
    INCONCLUSIVO,
    OK,
)


@pytest.fixture(autouse=True)
def spec_137_done():
    exigir_spec_done("137")


def test_criterio_1_yfinance_pula_yahoo(monkeypatch):
    """obter_referencia('yfinance') pula ref_yahoo e devolve a referência do Stooq."""
    ref_y = Referencia("Yahoo Finance", 130000.0, {})
    ref_s = Referencia("Stooq (^BVP)", 130500.0, {})

    def fake_ref_yahoo():
        return ref_y

    def fake_ref_stooq():
        return ref_s

    monkeypatch.setattr(auditar, "FONTES_REFERENCIA", [fake_ref_yahoo, fake_ref_stooq])

    ref, erros = obter_referencia("yfinance")
    assert ref is not None
    assert ref.fonte == "Stooq (^BVP)"
    assert ref.valor == 130500.0


def test_criterio_2_mt5_mais_yfinance_pula_yahoo(monkeypatch):
    """obter_referencia('mt5+yfinance') pula ref_yahoo."""
    ref_y = Referencia("Yahoo Finance", 130000.0, {})
    ref_s = Referencia("Stooq (^BVP)", 130500.0, {})

    chamou_yahoo = False

    def fake_ref_yahoo():
        nonlocal chamou_yahoo
        chamou_yahoo = True
        return ref_y

    def fake_ref_stooq():
        return ref_s

    monkeypatch.setattr(auditar, "FONTES_REFERENCIA", [fake_ref_yahoo, fake_ref_stooq])

    ref, erros = obter_referencia("mt5+yfinance")
    assert ref is not None
    assert ref.fonte == "Stooq (^BVP)"
    assert not chamou_yahoo


def test_criterio_3_mt5_usa_ref_yahoo_primeiro(monkeypatch):
    """obter_referencia('mt5') usa ref_yahoo primeiro."""
    ref_y = Referencia("Yahoo Finance", 130000.0, {})
    ref_s = Referencia("Stooq (^BVP)", 130500.0, {})

    def fake_ref_yahoo():
        return ref_y

    def fake_ref_stooq():
        return ref_s

    monkeypatch.setattr(auditar, "FONTES_REFERENCIA", [fake_ref_yahoo, fake_ref_stooq])

    ref, erros = obter_referencia("mt5")
    assert ref is not None
    assert ref.fonte == "Yahoo Finance"


def test_criterio_4_yfinance_stooq_fora_do_ar_inconclusivo(monkeypatch):
    """obter_referencia('yfinance') com o Stooq fora do ar devolve (None, erros), e checar_referencia produz ibov.fonte_independente como inconclusivo, sem nenhum OK."""

    def fake_ref_yahoo():
        return Referencia("Yahoo Finance", 130000.0, {})

    def fake_ref_stooq():
        raise ConnectionError("Stooq offline")

    monkeypatch.setattr(auditar, "FONTES_REFERENCIA", [fake_ref_yahoo, fake_ref_stooq])

    ref, erros = obter_referencia("yfinance")
    assert ref is None
    assert any("fake_ref_stooq" in e or "Stooq offline" in e for e in erros)

    painel = Painel(
        origem="snapshot",
        valor=130000.0,
        fonte="yfinance",
    )
    agora = datetime.now(timezone.utc)
    resultados = checar_referencia(painel, ref, erros, agora)

    assert len(resultados) == 1
    assert resultados[0].id == "ibov.fonte_independente"
    assert resultados[0].status == INCONCLUSIVO
    assert OK not in [r.status for r in resultados]


def test_criterio_5_rotulo_desconhecido_aviso_no_detalhe(monkeypatch):
    """Rótulo desconhecido ('xpto') não pula nada e aparece como aviso no detalhe."""
    ref_y = Referencia("Yahoo Finance", 130000.0, {})

    def fake_ref_yahoo():
        return ref_y

    monkeypatch.setattr(auditar, "FONTES_REFERENCIA", [fake_ref_yahoo])

    ref, erros = obter_referencia("xpto")
    assert ref is not None
    assert ref.fonte == "Yahoo Finance"
    assert any("fonte do produto desconhecida: xpto" in e for e in erros)

    painel = Painel(
        origem="snapshot",
        valor=130000.0,
        fonte="xpto",
    )
    agora = datetime.now(timezone.utc)
    resultados = checar_referencia(painel, ref, erros, agora)

    detalhes = " ".join(r.detalhe for r in resultados)
    assert "fonte do produto desconhecida: xpto" in detalhes


def test_criterio_6_detalhe_contem_produto_e_referencia():
    """O detalhe de ibov.confere_com_fonte contém produto: yfinance e o nome da referência usada."""
    painel = Painel(
        origem="snapshot",
        valor=130000.0,
        fonte="yfinance",
    )
    ref = Referencia("Stooq (^BVP)", 130050.0, {})
    agora = datetime.now(timezone.utc)

    resultados = checar_referencia(painel, ref, [], agora)
    confere = [r for r in resultados if r.id == "ibov.confere_com_fonte"][0]

    assert "produto: yfinance" in confere.detalhe
    assert "referência: Stooq (^BVP)" in confere.detalhe
