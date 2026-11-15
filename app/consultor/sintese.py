from datetime import datetime, timezone, timedelta

from app.consultor.armazenamento import ler_data, ler_preco_alvo


def calcular_consenso(opinioes, referencia: datetime | None = None):
    if not opinioes:
        return {
            "consenso": "cobertura insuficiente",
            "preco_alvo_mediano": None,
            "faixa": None,
            "potencial": None,
            "detalhes": {},
        }
    casas: dict[str, dict] = {}
    agora = referencia or datetime.now(timezone.utc)
    if agora.tzinfo is None:
        agora = agora.replace(tzinfo=timezone.utc)
    limite = agora - timedelta(days=30)
    for op in opinioes:
        # A data pode vir em ISO ou no formato do RSS (spec 158).
        data_op = ler_data(op.get("data_materia"))
        if data_op is None or data_op < limite:
            continue
        casa = op["casa"]
        if casa not in casas or data_op > casas[casa]["data"]:
            casas[casa] = {
                "recomendacao": op["recomendacao"],
                "preco_alvo": op["preco_alvo"],
                "data": data_op,
            }
    if len(casas) < 2:
        return {
            "consenso": "cobertura insuficiente",
            "preco_alvo_mediano": None,
            "faixa": None,
            "potencial": None,
            "detalhes": {},
        }

    compra = neutro = venda = 0
    alvos = []
    for casa, dados in casas.items():
        rec = dados["recomendacao"].lower()
        if rec == "compra":
            compra += 1
        elif rec == "venda":
            venda += 1
        else:
            neutro += 1

        alvo = ler_preco_alvo(dados["preco_alvo"])
        if alvo is not None:
            alvos.append(alvo)

    total = len(casas)
    if (
        compra >= total * (2.0 / 3.0)
        and compra > 0
        and (compra / float(total)) >= 0.66666667
    ):
        consenso = "compra"
    elif (
        venda >= total * (2.0 / 3.0)
        and venda > 0
        and (venda / float(total)) >= 0.66666667
    ):
        consenso = "venda"
    elif neutro >= total * (2.0 / 3.0) and neutro > 0:
        consenso = "neutro"
    else:
        consenso = "dividido"

    mediano = min_alvo = max_alvo = None
    if alvos:
        alvos.sort()
        n = len(alvos)
        mediano = (
            alvos[n // 2] if n % 2 != 0 else (alvos[n // 2 - 1] + alvos[n // 2]) / 2.0
        )
        min_alvo = alvos[0]
        max_alvo = alvos[-1]

    return {
        "consenso": consenso,
        "preco_alvo_mediano": mediano,
        "faixa": (min_alvo, max_alvo) if alvos else None,
        "potencial": None,  # Será preenchido com o preço atual depois
        "detalhes": {
            "compra": compra,
            "neutro": neutro,
            "venda": venda,
            "total": total,
        },
    }


def obter_decisao_final(avaliacao, consenso_casas, fechamento, mm21):
    tecnico = avaliacao["decisao"]
    consenso = consenso_casas["consenso"]
    potencial = consenso_casas.get("potencial")

    decisao = tecnico
    frase = ""
    gatilho = avaliacao.get("gatilho", "-")

    if tecnico == "Comprar":
        if consenso == "dividido":
            frase = "casas divididas"
        elif consenso == "neutro":
            frase = "casas neutras"
        elif consenso == "venda":
            decisao = "Aguardar"
            gatilho = "nova opinião de casa ou fechamento acima da máxima de 20 pregões"
            frase = "maioria das casas recomenda venda"
    elif tecnico == "Vender":
        if consenso == "dividido":
            frase = "casas divididas"
        elif consenso == "neutro":
            frase = "casas neutras"
        elif consenso == "compra":
            decisao = "Aguardar"
            mm200 = avaliacao.get("mm200", 0)
            gatilho = f"Fechamento acima da MM200 (R$ {mm200:.2f})"
            frase = "maioria das casas recomenda compra"
    elif tecnico == "Aguardar":
        decisao = "Aguardar"
    elif tecnico == "Sem sinal":
        if (
            consenso == "compra"
            and consenso_casas["detalhes"].get("total", 0) >= 3
            and potencial is not None
            and potencial >= 0.15
        ):
            decisao = "No radar"
            mm21_val = mm21 if mm21 is not None else 0
            gatilho = f"fechamento acima da MM21 (R$ {mm21_val:.2f})"
            frase = "casas recomendam compra com potencial"

    return decisao, frase, gatilho
