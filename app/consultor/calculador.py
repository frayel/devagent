import json
from datetime import timezone, timedelta
from app.database import get_historico_diario
from app.consultor.universo import CARTEIRA_IBOVESPA
from app.consultor.regras import avaliar_ativo
from app.database import get_consultor_confianca_regras
from datetime import datetime


def calcular_consultor():
    ativos = CARTEIRA_IBOVESPA + ["^BVSP"]
    historicos = get_historico_diario(ativos, "1y", "1d", max_age_minutes=15)

    if "^BVSP" not in historicos or not historicos["^BVSP"]:
        raise ValueError("Dados do Ibovespa indisponíveis")

    ibov_data = json.loads(historicos["^BVSP"]["dados_json"])
    ibov_closes = ibov_data.get("closes", [])

    resultados = {"Comprar": [], "Vender": [], "Aguardar": [], "Sem sinal": []}

    try:
        ts = datetime.fromisoformat(historicos["^BVSP"]["timestamp"])
        timestamp = ts.astimezone(timezone(timedelta(hours=-3))).strftime(
            "%d/%m/%Y %H:%M:%S BRT"
        )
    except Exception:
        timestamp = "-"

    regras_confianca = get_consultor_confianca_regras()

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

        dados_json = json.loads(historicos[ticker]["dados_json"])
        closes = dados_json.get("closes", [])
        volumes = dados_json.get("volumes", [])

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

        resultados[avaliacao["decisao"]].append(
            {
                "ticker": ticker,
                "fechamento": closes[-1],
                "regra": avaliacao["regra"],
                "motivo": avaliacao["motivo"],
                "gatilho": avaliacao["gatilho"],
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

    return {
        "resultados": resultados,
        "ativos_avaliados": len(CARTEIRA_IBOVESPA),
        "regras_confianca": regras_summary,
    }
