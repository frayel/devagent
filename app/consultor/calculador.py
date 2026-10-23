from datetime import timezone, timedelta
from app.database import get_historico_diario
from app.consultor.universo import CARTEIRA_IBOVESPA
from app.consultor.sintese import calcular_consenso, obter_decisao_final
from app.consultor.regras import avaliar_ativo, calcular_mm
from app.consultor.armazenamento import (
    get_opinioes_ativos,
    get_opinioes_recentes,
    get_opinioes_status,
)
from app.consultor.avaliador_historico import pre_processar_ativo
from app.database import get_consultor_confianca
from datetime import datetime

# O coletor consultor_historico grava a série diária de 2 anos e a renova a
# cada hora. Quatro dias de tolerância atravessam fim de semana e feriado.
JANELA = "2y"
IDADE_MAXIMA_MIN = 60 * 24 * 4


def calcular_consultor():
    ativos = CARTEIRA_IBOVESPA + ["^BVSP"]
    historicos = get_historico_diario(
        ativos, JANELA, "1d", max_age_minutes=IDADE_MAXIMA_MIN
    )

    if "^BVSP" not in historicos or not historicos["^BVSP"]:
        return {"ibovespa": None, "opinioes_recentes": [], "regras_confianca": {}}

    ibov_closes, _, ibov_ts = pre_processar_ativo(historicos["^BVSP"])

    resultados = {
        "Comprar": [],
        "Vender": [],
        "Aguardar": [],
        "No radar": [],
        "Sem sinal": [],
    }

    try:
        ts = datetime.fromtimestamp(ibov_ts[-1], timezone.utc)
        timestamp = ts.astimezone(timezone(timedelta(hours=-3))).strftime(
            "%d/%m/%Y %H:%M:%S BRT"
        )
    except Exception:
        timestamp = "-"

    regras_confianca = get_consultor_confianca()

    def obter_confianca(nome_regra):
        if not regras_confianca or nome_regra not in regras_confianca:
            return {"nivel": "baixa", "mensagem": "histórico indisponível"}

        dados = regras_confianca[nome_regra]
        n = dados["disparos"]
        acertos = dados["acertos"]
        excesso = dados["excesso_mediano"]

        if n == 0:
            return {"nivel": "baixa", "mensagem": "histórico indisponível"}

        taxa = (acertos / n) * 100

        if n >= 100 and taxa >= 60:
            nivel = "alta"
        elif n >= 30 and taxa >= 55:
            nivel = "média"
        elif n < 30:
            return {"nivel": "baixa", "mensagem": f"baixa: amostra pequena (n = {n})"}
        else:
            nivel = "baixa"

        sinal = "+" if excesso > 0 else ""
        mensagem = f"Nas {n} vezes em que {nome_regra.split(' ')[0]} disparou em ativos do Ibovespa nos últimos 2 anos, o ativo superou o Ibovespa em {int(taxa)}% dos casos nos 20 pregões seguintes (mediana {sinal}{(excesso * 100):.1f} p.p.)."

        return {
            "nivel": nivel,
            "mensagem": mensagem,
            "n": n,
            "taxa_acerto": taxa,
            "excesso_mediano": excesso,
            "janela_inicio": dados.get("janela_inicio", ""),
            "janela_fim": dados.get("janela_fim", ""),
            "confianca": nivel,
        }

    opinioes_ativos = get_opinioes_ativos()
    opinioes_recentes = get_opinioes_recentes()
    opinioes_status = get_opinioes_status()

    for ticker in CARTEIRA_IBOVESPA:
        if ticker not in historicos:
            resultados["Sem sinal"].append(
                {
                    "ticker": ticker,
                    "fechamento": 0,
                    "regra": "R0 Sem sinal",
                    "motivo": "Sem dados",
                    "gatilho": "-",
                    "fonte": "-",
                    "timestamp": timestamp,
                }
            )
            continue

        closes, volumes, _ = pre_processar_ativo(historicos[ticker])

        if len(closes) < 220:
            resultados["Sem sinal"].append(
                {
                    "ticker": ticker,
                    "fechamento": closes[-1] if closes else 0,
                    "regra": "R0 Sem sinal",
                    "motivo": "Menos de 220 pregões",
                    "gatilho": "-",
                    "fonte": "yfinance",
                    "timestamp": timestamp,
                }
            )
            continue

        avaliacao = avaliar_ativo(ticker, closes, volumes, ibov_closes)
        confianca_dados = obter_confianca(avaliacao["regra"])

        opinioes_ticker = opinioes_ativos.get(ticker, [])
        consenso_dados = calcular_consenso(opinioes_ticker)

        if consenso_dados["preco_alvo_mediano"] and closes[-1] > 0:
            consenso_dados["potencial"] = (
                consenso_dados["preco_alvo_mediano"] / closes[-1]
            ) - 1

        mm21 = calcular_mm(closes, 21)
        decisao_final, justificativa, gatilho_final = obter_decisao_final(
            avaliacao, consenso_dados, closes[-1], mm21
        )

        resultados[decisao_final].append(
            {
                "ticker": ticker,
                "opinioes": opinioes_ticker,
                "consenso": consenso_dados,
                "justificativa": justificativa,
                "decisao_tecnica": avaliacao["decisao"],
                "fechamento": closes[-1],
                "regra": avaliacao["regra"],
                "motivo": avaliacao["motivo"],
                "gatilho": gatilho_final,
                "fonte": "yfinance",
                "timestamp": timestamp,
                "confianca": confianca_dados.get(
                    "confianca", confianca_dados.get("nivel")
                ),
                "n": confianca_dados.get("n", 0),
                "taxa_acerto": confianca_dados.get("taxa_acerto", 0.0),
                "excesso_mediano": confianca_dados.get("excesso_mediano", 0.0),
                "janela_inicio": confianca_dados.get("janela_inicio", ""),
                "janela_fim": confianca_dados.get("janela_fim", ""),
                "mensagem_confianca": confianca_dados["mensagem"],
            }
        )

    # Extract rules confidence summary to return along with the result
    regras_summary = {}
    for regra in [
        "R1 Faca caindo",
        "R2 Tendência de baixa",
        "R3 Esticada",
        "R4 Rompimento pendente",
        "R5 Tendência de alta saudável",
    ]:
        regras_summary[regra] = obter_confianca(regra)

    res_dict = {
        "resultados": resultados,
        "ativos_avaliados": len(CARTEIRA_IBOVESPA),
        "regras_confianca": regras_summary,
        "opinioes_recentes": opinioes_recentes,
        "opinioes_status": opinioes_status,
    }

    # Trigger saves for recomendacoes & fechamentos
    try:
        from app.consultor.armazenamento import save_recomendacoes, save_fechamentos

        flat_resultados = []
        for group_name, items in resultados.items():
            for item in items:
                flat_resultados.append(
                    {
                        "ticker": item["ticker"],
                        "timestamp": item["timestamp"],
                        "decisao": group_name,
                        "regra": item["regra"],
                        "consenso": str(item.get("consenso", "")),
                        "preco": item.get("fechamento", 0.0),
                        "gatilho": str(item.get("gatilho", "-")),
                    }
                )
        save_recomendacoes(flat_resultados)
        save_fechamentos(flat_resultados)
    except Exception:
        pass

    return res_dict
