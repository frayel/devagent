from datetime import datetime, timezone, timedelta


def calcular_consenso(opinioes):
    if not opinioes:
        return {
            "consenso": "cobertura insuficiente",
            "preco_alvo_mediano": None,
            "faixa": None,
            "potencial": None,
            "detalhes": {},
        }
    casas = {}
    limite = datetime.now(timezone.utc) - timedelta(days=30)
    for op in opinioes:
        dt_str = (
            op["data_materia"].replace("Z", "+00:00")
            if "Z" in op["data_materia"]
            else op["data_materia"]
        )
        try:
            data_op = datetime.fromisoformat(dt_str)
        except ValueError:
            continue
        if data_op.tzinfo is None:
            data_op = data_op.replace(tzinfo=timezone.utc)
        if data_op < limite:
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

        if dados["preco_alvo"]:
            alvos.append(float(dados["preco_alvo"]))

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
        elif consenso == "venda":
            decisao = "Aguardar"
            gatilho = "nova opinião de casa ou fechamento acima da máxima de 20 pregões"
            frase = "maioria das casas recomenda venda"
    elif tecnico == "Vender":
        if consenso == "dividido":
            frase = "casas divididas"
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
