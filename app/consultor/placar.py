from datetime import datetime
from typing import Any

from app.consultor.sintese import agrupar_por_ativo, fechamentos_das_opinioes


def _calcular_excesso(
    preco_inicial: float,
    preco_final: float,
    ibov_inicial: float,
    ibov_final: float,
) -> float:
    retorno_ativo = (preco_final / preco_inicial) - 1.0
    retorno_ibov = (ibov_final / ibov_inicial) - 1.0
    return retorno_ativo - retorno_ibov


GRUPOS_DO_CONSULTOR = ("Comprar", "Vender", "Aguardar", "No radar", "Sem sinal")


def _fechamentos_das_recomendacoes(
    tickers: list[str],
) -> tuple[list[str], dict[tuple[str, str], float]]:
    """Os pregões de `consultor_fechamentos` e os fechamentos dos tickers e do
    `^BVSP`, numa conexão e duas consultas (spec 131)."""
    from app.consultor import armazenamento

    armazenamento.init_db()
    conn, backend = armazenamento.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT data_pregao FROM consultor_fechamentos ORDER BY data_pregao ASC"
        )
        pregoes = sorted({x[0] for x in cur.fetchall()})

        pedidos = sorted(set(tickers) | {"^BVSP"})
        marcadores = ",".join("?" for _ in pedidos)
        cur.execute(
            armazenamento.sql_para(
                backend,
                "SELECT data_pregao, ticker, preco_fechamento FROM consultor_fechamentos "
                f"WHERE ticker IN ({marcadores})",
            ),
            pedidos,
        )
        fechamentos = {(dp, t): preco for dp, t, preco in cur.fetchall()}
    finally:
        conn.close()
    return pregoes, fechamentos


def _mensagem_do_placar(
    recomendacao: dict,
    pregoes: list[str],
    fechamentos: dict[tuple[str, str], float],
) -> str:
    """ "+X% contra o IBOV em N pregões" de uma recomendação gravada, ou
    "ainda sem resultado" sem pregão futuro ou sem algum fechamento."""
    dp_rec = recomendacao["timestamp"][:10]
    if dp_rec not in pregoes:
        return "ainda sem resultado"
    idx = pregoes.index(dp_rec)
    offset = min(5, len(pregoes) - 1 - idx)
    if offset <= 0:
        return "ainda sem resultado"
    dp_futuro = pregoes[idx + offset]
    p_futuro = fechamentos.get((dp_futuro, recomendacao["ticker"]))
    ibov_hoje = fechamentos.get((dp_rec, "^BVSP"))
    ibov_futuro = fechamentos.get((dp_futuro, "^BVSP"))
    if p_futuro is None or ibov_hoje is None or ibov_futuro is None:
        return "ainda sem resultado"
    excesso = _calcular_excesso(recomendacao["preco"], p_futuro, ibov_hoje, ibov_futuro)
    sinal = "+" if excesso > 0 else ""
    return f"{sinal}{excesso * 100:.1f}% contra o IBOV em {offset} pregões"


def consultor_de_pregao_passado(data: str, referencia: datetime | None) -> dict:
    """O Consultor de um pregão passado, como `/consultor?data=` e
    `/api/consultor?data=` mostram: as recomendações gravadas naquele pregão,
    cada uma com o placar contra o IBOV, e as opiniões daquele dia (spec 193)."""
    from app.consultor import armazenamento

    hist = armazenamento.get_recomendacoes(data)
    pregoes, fechamentos = _fechamentos_das_recomendacoes([r["ticker"] for r in hist])

    resultados: dict[str, list[Any]] = {grupo: [] for grupo in GRUPOS_DO_CONSULTOR}
    for row in hist:
        grupo = row["decisao"]
        resultados.setdefault(grupo, []).append(
            {
                "ticker": row["ticker"],
                "fechamento": row["preco"],
                "regra": row["regra"],
                "gatilho": row["gatilho"],
                "consenso": armazenamento.ler_consenso(row["consenso"]),
                "justificativa": "",
                "motivo": row["regra"],
                "timestamp": row["timestamp"],
                "mensagem_confianca": _mensagem_do_placar(row, pregoes, fechamentos),
                "decisao_tecnica": row["decisao"],
            }
        )

    opinioes = armazenamento.get_opinioes_historicas(data)
    return {
        "resultados": resultados,
        "ativos_avaliados": len(hist),
        "regras_confianca": {},
        "opinioes_recentes": opinioes,
        "opinioes_por_ativo": agrupar_por_ativo(
            opinioes,
            referencia=referencia,
            fechamentos=fechamentos_das_opinioes(opinioes, ate=data),
        ),
        "opinioes_status": {},
    }
