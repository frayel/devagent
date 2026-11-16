"""Issue #910: a referência que ainda não cotou o pregão do dia não reprova a variação.

Às 10:59 de 16/11/2026 o Yahoo devolvia como cotação de ^BVSP o fechamento de 13/11
(172.457,77). A variação de referência saiu -0,00% e a checagem reprovou a variação
correta do produto (-0,98%); às 11:28 a mesma fonte já dava -1,04%.
"""

from datetime import datetime, timezone

from auditoria.auditar import (
    FALHA,
    INCONCLUSIVO,
    OK,
    Painel,
    Referencia,
    checar_referencia,
)

AGORA = datetime(2026, 11, 16, 13, 59, tzinfo=timezone.utc)
DATAS = ["2026-11-12", "2026-11-13", "2026-11-16"]
FECHAMENTOS_REF = {"2026-11-12": 171324.0, "2026-11-13": 172458.0}


def _painel(variacao_pct: float) -> Painel:
    return Painel(
        origem="snapshot",
        valor=170767.0,
        variacao=170767.0 - 172458.0,
        variacao_pct=variacao_pct,
        fechamento_anterior=172458.0,
        datas=DATAS,
        fechamentos=[171324.0, 172458.0, 170767.0],
        fonte="mt5",
    )


def _variacao(ref: Referencia, variacao_pct: float = -0.98):
    por_id = {r.id: r for r in checar_referencia(_painel(variacao_pct), ref, [], AGORA)}
    return por_id["ibov.variacao_confere_com_fonte"]


def test_referencia_sem_cotacao_do_dia_e_inconclusiva():
    ref = Referencia(
        "Yahoo Finance (^BVSP)", 172457.77, dict(FECHAMENTOS_REF), "2026-11-13"
    )
    r = _variacao(ref)
    assert r.status == INCONCLUSIVO
    assert "sem cotação do pregão de 2026-11-16" in r.detalhe


def test_referencia_com_cotacao_do_dia_continua_conferindo():
    ref = Referencia(
        "Yahoo Finance (^BVSP)", 170664.48, dict(FECHAMENTOS_REF), "2026-11-16"
    )
    assert _variacao(ref, -1.24).status == OK
    assert _variacao(ref, +1.24).status == FALHA


def test_referencia_sem_data_da_cotacao_continua_conferindo():
    """Fonte que não informa a data da cotação (Stooq) segue como antes."""
    ref = Referencia("Stooq (^BVP)", 172457.77, dict(FECHAMENTOS_REF))
    assert _variacao(ref).status == FALHA


def test_ref_yahoo_le_a_data_da_cotacao(monkeypatch):
    import io
    import json

    from auditoria import auditar

    corpo = {
        "chart": {
            "result": [
                {
                    # 13/11/2026 17:00 BRT = 20:00 UTC
                    "meta": {
                        "regularMarketPrice": 172457.77,
                        "regularMarketTime": 1794600000,
                    },
                    "timestamp": [1794574800],
                    "indicators": {"quote": [{"close": [172458.0]}]},
                }
            ]
        }
    }
    monkeypatch.setattr(
        auditar.urllib.request,
        "urlopen",
        lambda *a, **k: io.BytesIO(json.dumps(corpo).encode()),
    )
    ref = auditar.ref_yahoo()
    assert ref.ultima_cotacao == "2026-11-13"
    assert ref.fechamentos == {"2026-11-13": 172458.0}
