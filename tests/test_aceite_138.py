from datetime import datetime, timezone

from auditoria.auditar import (
    FALHA,
    INCONCLUSIVO,
    OK,
    Painel,
    Referencia,
    checar_coerencia,
    checar_referencia,
    extrair_do_snapshot,
)

AGORA = datetime(2026, 11, 4, 18, 0, tzinfo=timezone.utc)


def _criar_painel(
    valor: float,
    fechamento_anterior: float | None,
    fechamentos: list[float],
    datas: list[str],
    variacao_pct: float | None = None,
    fonte: str | None = "mt5",
) -> Painel:
    return Painel(
        origem="snapshot",
        valor=valor,
        variacao=valor - fechamento_anterior
        if fechamento_anterior is not None
        else None,
        variacao_pct=variacao_pct
        if variacao_pct is not None
        else (
            ((valor / fechamento_anterior) - 1) * 100 if fechamento_anterior else 0.0
        ),
        fechamento_anterior=fechamento_anterior,
        datas=datas,
        fechamentos=fechamentos,
        fonte=fonte,
    )


def _historico_padrao(n: int = 20) -> tuple[list[str], list[float]]:
    datas = [f"2026-10-{i:02d}" for i in range(1, n + 1)]
    fechamentos = [120000.0 + i * 500 for i in range(n)]
    return datas, fechamentos


def test_fechamento_anterior_incoerente_falha():
    """Snapshot com valor = 131300, fechamentos[-1] = 131300, fechamentos[-2] = 130000 e

    fechamento_anterior = 105000: ibov.fechamento_anterior_coerente falha,
    com os dois números na mensagem.
    """
    datas, fechamentos = _historico_padrao(18)
    fechamentos[-2] = 130000.0
    fechamentos[-1] = 131300.0
    p = _criar_painel(
        valor=131300.0,
        fechamento_anterior=105000.0,
        fechamentos=fechamentos,
        datas=datas,
    )

    resultados = checar_coerencia(p)
    por_id = {r.id: r for r in resultados}
    assert "ibov.fechamento_anterior_coerente" in por_id
    r = por_id["ibov.fechamento_anterior_coerente"]
    assert r.status == FALHA
    assert "105000" in r.detalhe
    assert "130000" in r.detalhe


def test_fechamento_anterior_coerente_passa():
    """O mesmo snapshot com fechamento_anterior = 130000: passa."""
    datas, fechamentos = _historico_padrao(18)
    fechamentos[-2] = 130000.0
    fechamentos[-1] = 131300.0
    p = _criar_painel(
        valor=131300.0,
        fechamento_anterior=130000.0,
        fechamentos=fechamentos,
        datas=datas,
    )

    resultados = checar_coerencia(p)
    por_id = {r.id: r for r in resultados}
    assert "ibov.fechamento_anterior_coerente" in por_id
    r = por_id["ibov.fechamento_anterior_coerente"]
    assert r.status == OK
    assert "130000" in r.detalhe


def test_fechamento_anterior_antes_abertura_inconclusivo():
    """Snapshot com valor = 131900 e fechamentos[-1] = 131300 (antes da abertura): inconclusivo."""
    datas, fechamentos = _historico_padrao(18)
    fechamentos[-2] = 130000.0
    fechamentos[-1] = 131300.0
    p = _criar_painel(
        valor=131900.0,
        fechamento_anterior=130000.0,
        fechamentos=fechamentos,
        datas=datas,
    )

    resultados = checar_coerencia(p)
    por_id = {r.id: r for r in resultados}
    assert "ibov.fechamento_anterior_coerente" in por_id
    r = por_id["ibov.fechamento_anterior_coerente"]
    assert r.status == INCONCLUSIVO


def test_variacao_confere_com_fonte_falha():
    """Referência com fechamentos = {'2026-11-02': 130000, '2026-11-03': 131300} e

    página com variacao_pct = +12,87 e último ponto em 2026-11-03:
    ibov.variacao_confere_com_fonte falha (referência +1,00%).
    """
    ref = Referencia(
        fonte="Stooq (^BVP)",
        valor=131300.0,
        fechamentos={"2026-11-02": 130000.0, "2026-11-03": 131300.0},
    )
    p = _criar_painel(
        valor=131300.0,
        fechamento_anterior=130000.0,
        fechamentos=[130000.0, 131300.0],
        datas=["2026-11-02", "2026-11-03"],
        variacao_pct=12.87,
        fonte="mt5",
    )

    resultados = checar_referencia(p, ref, [], AGORA)
    por_id = {r.id: r for r in resultados}
    assert "ibov.variacao_confere_com_fonte" in por_id
    r = por_id["ibov.variacao_confere_com_fonte"]
    assert r.status == FALHA
    assert "+12.87%" in r.detalhe
    assert "+1.00%" in r.detalhe


def test_variacao_confere_com_fonte_limiares():
    """Mesma referência e página com +1,20%: passa; com +1,60%: falha (diferença de 0,60 p.p.)."""
    ref = Referencia(
        fonte="Stooq (^BVP)",
        valor=131300.0,
        fechamentos={"2026-11-02": 130000.0, "2026-11-03": 131300.0},
    )

    # Com +1,20% -> diferença de 0,20 p.p. <= 0,5 p.p. -> passa
    p_passa = _criar_painel(
        valor=131300.0,
        fechamento_anterior=130000.0,
        fechamentos=[130000.0, 131300.0],
        datas=["2026-11-02", "2026-11-03"],
        variacao_pct=1.20,
        fonte="mt5",
    )
    res_passa = checar_referencia(p_passa, ref, [], AGORA)
    por_id_passa = {r.id: r for r in res_passa}
    assert por_id_passa["ibov.variacao_confere_com_fonte"].status == OK

    # Com +1,60% -> diferença de 0,60 p.p. > 0,5 p.p. -> falha
    p_falha = _criar_painel(
        valor=131300.0,
        fechamento_anterior=130000.0,
        fechamentos=[130000.0, 131300.0],
        datas=["2026-11-02", "2026-11-03"],
        variacao_pct=1.60,
        fonte="mt5",
    )
    res_falha = checar_referencia(p_falha, ref, [], AGORA)
    por_id_falha = {r.id: r for r in res_falha}
    assert por_id_falha["ibov.variacao_confere_com_fonte"].status == FALHA


def test_sem_referencia_ou_excluida_e_inconclusivo():
    """Sem referência, ou com a referência excluída pela spec 137:

    inconclusivo, o código de saída da auditoria continua 0 por causa dessas duas checagens.
    """
    p_sem_ref = _criar_painel(
        valor=131300.0,
        fechamento_anterior=130000.0,
        fechamentos=[130000.0, 131300.0],
        datas=["2026-11-02", "2026-11-03"],
        variacao_pct=1.00,
        fonte="mt5",
    )
    res_sem_ref = checar_referencia(p_sem_ref, None, ["todas as fontes offline"], AGORA)
    # Nenhuma falha é gerada, apenas inconclusivo
    assert not any(r.status == FALHA for r in res_sem_ref)
    assert any(r.status == INCONCLUSIVO for r in res_sem_ref)

    # Referência excluída pela fonte do produto (ex.: produto usou yfinance e ref é Yahoo Finance)
    p_mesma_fonte = _criar_painel(
        valor=131300.0,
        fechamento_anterior=130000.0,
        fechamentos=[130000.0, 131300.0],
        datas=["2026-11-02", "2026-11-03"],
        variacao_pct=1.00,
        fonte="yfinance",
    )
    ref_yahoo = Referencia(
        fonte="Yahoo Finance (^BVSP)",
        valor=131300.0,
        fechamentos={"2026-11-02": 130000.0, "2026-11-03": 131300.0},
    )
    res_mesma_fonte = checar_referencia(p_mesma_fonte, ref_yahoo, [], AGORA)
    por_id = {r.id: r for r in res_mesma_fonte}
    assert "ibov.variacao_confere_com_fonte" in por_id
    assert por_id["ibov.variacao_confere_com_fonte"].status == INCONCLUSIVO
    # Código de saída não deve falhar
    assert not any(
        r.status == FALHA
        for r in [
            por_id["ibov.variacao_confere_com_fonte"],
            *checar_coerencia(p_mesma_fonte),
        ]
        if r.id
        in ["ibov.fechamento_anterior_coerente", "ibov.variacao_confere_com_fonte"]
    )


def test_compatibilidade_com_extrair_do_snapshot():
    """Valida extrair_do_snapshot diretamente com as novas checagens."""
    dados_snapshot = {
        "paineis": {
            "ibovespa": {
                "valor": 131300.0,
                "fechamento_anterior": 105000.0,
                "variacao_pct": 1.0,
                "fonte": "mt5",
                "historico": {
                    "datas": [f"2026-10-{i:02d}" for i in range(1, 19)],
                    "fechamentos": [120000.0 + i * 500 for i in range(16)]
                    + [130000.0, 131300.0],
                },
            }
        }
    }
    p = extrair_do_snapshot(dados_snapshot)
    assert p is not None
    resultados = checar_coerencia(p)
    por_id = {r.id: r for r in resultados}
    assert por_id["ibov.fechamento_anterior_coerente"].status == FALHA
    assert "105000" in por_id["ibov.fechamento_anterior_coerente"].detalhe
