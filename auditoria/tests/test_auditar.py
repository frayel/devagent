"""Testes do auditor. Não acessam a rede."""

from datetime import date, datetime, timedelta, timezone

from auditoria import calendario
from auditoria.auditar import (
    FALHA,
    INCONCLUSIVO,
    Painel,
    Referencia,
    checar_coerencia,
    checar_fixtures,
    checar_frescor,
    checar_referencia,
    extrair_do_html,
    numeros_dos_fixtures,
)

# Réplica do HTML servido em produção em 26/09/2026, com o dado de teste.
HTML_INCIDENTE = """
<h2>Ibovespa Hoje</h2>
<div style="font-size: 2em; font-weight: bold;">
    130.000 pontos
</div>
<div class="positive">+1.000 (+0.78%)</div>
<div class="text-small">Última atualização: 26/09/2026 03:23:25 UTC</div>
<script>
    const historyData = {"dates": ["2023-09-25", "2023-09-26", "2023-09-27"],
                         "closes": [128000.0, 129000.0, 130000.5]};
</script>
<footer>Conteúdo informativo gerado automaticamente. Não constitui recomendação de investimento.</footer>
"""

# Números do fixture que vazou (tests/fixtures/brapi_response.json em 26/09/2026).
# Fixos aqui para o teste não depender de fixtures que o desenvolvedor pode mudar.
FIXTURE_DO_INCIDENTE = {128000.0, 129000.0, 130000.5}

# 26/09/2026 é sábado; o último pregão é sexta, 25/09.
AGORA = datetime(2026, 9, 26, 5, 0, tzinfo=timezone.utc)


def _falhas(resultados):
    return {r.id for r in resultados if r.status == FALHA}


def _pregoes_ate(fim: date, n: int) -> list[str]:
    dias = [fim]
    while len(dias) < n:
        dias.append(calendario.pregao_anterior(dias[-1]))
    return [d.isoformat() for d in reversed(dias)]


def _painel_saudavel() -> Painel:
    datas = _pregoes_ate(date(2026, 9, 25), 22)
    fech = [180_000.0 + i * 150 for i in range(len(datas))]
    return Painel(
        origem="html",
        valor=fech[-1],
        variacao=150.0,
        variacao_pct=150 / (fech[-1] - 150) * 100,
        fechamento_anterior=fech[-1] - 150,
        coletado_em=datetime(2026, 9, 25, 20, 45, tzinfo=timezone.utc),
        datas=datas,
        fechamentos=fech,
    )


def test_extrai_painel_do_html():
    p = extrair_do_html(HTML_INCIDENTE)
    assert p is not None
    assert p.valor == 130_000
    assert p.variacao == 1_000
    assert p.variacao_pct == 0.78
    assert p.coletado_em == datetime(2026, 9, 26, 3, 23, 25, tzinfo=timezone.utc)
    assert p.datas[-1] == "2023-09-27"


def test_html_sem_dados():
    assert extrair_do_html("<p>Dados não disponíveis no momento.</p>") is None


def test_incidente_do_ibovespa_seria_detectado():
    """Regressão: o bug de 26/09/2026 tem que reprovar por três caminhos."""
    p = extrair_do_html(HTML_INCIDENTE)
    assert p is not None
    ref = Referencia(
        "teste",
        183_476.86,
        {d: 183_000.0 for d in _pregoes_ate(date(2026, 9, 25), 20)},
    )
    falhas = _falhas(
        checar_frescor(p, AGORA)
        + checar_fixtures(p, FIXTURE_DO_INCIDENTE)
        + checar_referencia(p, ref, [], AGORA)
    )
    assert "ibov.historico_atual" in falhas
    assert "ibov.sem_dado_de_teste" in falhas
    assert "ibov.confere_com_fonte" in falhas
    assert "ibov.historico_tamanho" in _falhas(checar_coerencia(p))


def test_painel_saudavel_passa():
    p = _painel_saudavel()
    ref = Referencia("teste", p.valor, {d: c for d, c in zip(p.datas, p.fechamentos)})
    resultados = (
        checar_coerencia(p)
        + checar_frescor(p, AGORA)
        + checar_fixtures(p, FIXTURE_DO_INCIDENTE)
        + checar_referencia(p, ref, [], AGORA)
    )
    assert _falhas(resultados) == set(), [r for r in resultados if r.status == FALHA]


def test_variacao_incoerente_reprova():
    p = _painel_saudavel()
    p.variacao_pct = 3.5
    assert "ibov.variacao_coerente" in _falhas(checar_coerencia(p))


def test_coleta_parada_no_pregao_reprova():
    p = _painel_saudavel()
    quarta_14h = datetime(2026, 9, 23, 17, 0, tzinfo=timezone.utc)
    p.coletado_em = quarta_14h - timedelta(hours=2)
    p.datas = _pregoes_ate(date(2026, 9, 23), 22)
    assert "ibov.coleta_recente" in _falhas(checar_frescor(p, quarta_14h))


def test_fonte_fora_do_ar_e_inconclusivo():
    r = checar_referencia(_painel_saudavel(), None, ["yahoo: timeout"], AGORA)
    assert [x.status for x in r] == [INCONCLUSIVO]


def test_calendario_b3():
    assert calendario.pascoa(2026) == date(2026, 4, 5)
    assert not calendario.e_pregao(date(2026, 2, 17))  # Carnaval
    assert not calendario.e_pregao(date(2026, 4, 3))  # Sexta-feira Santa
    assert not calendario.e_pregao(date(2026, 11, 20))  # Consciência Negra
    assert calendario.e_pregao(date(2026, 9, 25))
    assert calendario.ultimo_pregao_iniciado(AGORA) == date(2026, 9, 25)
    antes_da_abertura = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)  # 9h BRT
    assert calendario.ultimo_pregao_iniciado(antes_da_abertura) == date(2026, 9, 25)


def test_le_numeros_dos_fixtures(tmp_path):
    (tmp_path / "f.json").write_text('{"a": [{"p": 130000.5, "d": 3}], "t": true}')
    assert numeros_dos_fixtures(tmp_path) == {130000.5}
