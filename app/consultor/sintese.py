import logging
from datetime import datetime, timezone, timedelta

from app.consultor.armazenamento import get_fechamentos, ler_data, ler_preco_alvo

logger = logging.getLogger(__name__)


JANELA_CONSENSO = timedelta(days=30)


def _limite_janela(referencia: datetime | None) -> datetime:
    agora = referencia or datetime.now(timezone.utc)
    if agora.tzinfo is None:
        agora = agora.replace(tzinfo=timezone.utc)
    return agora - JANELA_CONSENSO


def ultima_por_casa(
    opinioes: list[dict], referencia: datetime | None = None
) -> dict[str, dict]:
    """Casa -> a opinião mais recente dela, com `data_materia` nos 30 dias até `referencia`.

    Sem teto superior: data posterior à referência continua valendo, como
    sempre valeu no consenso. Data ilegível fica de fora (spec 165).
    """
    limite = _limite_janela(referencia)
    casas: dict[str, dict] = {}
    datas: dict[str, datetime] = {}
    for op in opinioes:
        # A data pode vir em ISO ou no formato do RSS (spec 158).
        data_op = ler_data(op.get("data_materia"))
        if data_op is None or data_op < limite:
            continue
        casa = op["casa"]
        if casa not in casas or data_op > datas[casa]:
            casas[casa] = op
            datas[casa] = data_op
    return casas


def _classe_recomendacao(recomendacao) -> str:
    rec = str(recomendacao or "").lower()
    if rec in ("compra", "venda"):
        return rec
    return "neutro"


_ROTULOS_CONTAGEM = (("compra", "Comprar"), ("neutro", "Neutro"), ("venda", "Vender"))


def situacao_do_alvo(
    opiniao: dict, fechamentos: list[tuple[str, float]]
) -> dict | None:
    """Se o preço-alvo da opinião já foi atingido ou quanto falta (spec 190).

    `fechamentos` é a lista do ticker da opinião, crescente por data. O sentido
    vem do fechamento anterior ao dia (Brasília) da matéria; sem ele, `None`.
    """
    alvo = ler_preco_alvo(opiniao.get("preco_alvo"))
    if alvo is None or alvo <= 0:
        return None
    momento = ler_data(opiniao.get("data_materia"))
    if momento is None:
        return None
    from app.services.carimbo import FUSO

    dia = momento.astimezone(FUSO).strftime("%Y-%m-%d")
    antes = [(d, p) for d, p in fechamentos if d < dia]
    if not antes:
        return None
    base_data, base_preco = antes[-1]
    if alvo > base_preco:
        sentido = "alta"
    elif alvo < base_preco:
        sentido = "baixa"
    else:
        return None
    situacao = {
        "sentido": sentido,
        "alvo": alvo,
        "base_data": base_data,
        "base_preco": base_preco,
    }
    for data, preco in fechamentos:
        if data < dia:
            continue
        if (sentido == "alta" and preco >= alvo) or (
            sentido == "baixa" and preco <= alvo
        ):
            return {"estado": "atingido", **situacao, "data": data, "preco": preco}
    data, preco = fechamentos[-1]
    return {
        "estado": "falta",
        **situacao,
        "data": data,
        "preco": preco,
        "distancia": alvo / preco - 1,
    }


def fechamentos_das_opinioes(
    opinioes: list[dict], ate: str | None = None
) -> dict[str, list[tuple[str, float]]]:
    """Os fechamentos guardados dos tickers que têm opinião (spec 190).

    Erro de leitura vira `{}` e um registro no log: a coluna sai `-` e a
    página não cai.
    """
    tickers = sorted({op["ticker"] for op in opinioes if op.get("ticker")})
    try:
        return get_fechamentos(tickers, ate=ate)
    except Exception:
        logger.exception("Falha ao ler consultor_fechamentos para a spec 190")
        return {}


def agrupar_por_ativo(
    opinioes: list[dict],
    referencia: datetime | None = None,
    fechamentos: dict[str, list[tuple[str, float]]] | None = None,
) -> list[dict]:
    """Uma linha por ativo para a lista Opiniões Recentes (spec 165).

    A contagem usa a mesma regra do consenso (`ultima_por_casa`), e
    `cobertura_insuficiente` pergunta ao próprio `calcular_consenso`. Cada
    opinião da linha é uma cópia com `alvo_situacao` (spec 190).
    """
    fechamentos = fechamentos or {}
    limite = _limite_janela(referencia)
    por_ticker: dict[str, list[dict]] = {}
    for op in opinioes:
        ticker = op.get("ticker")
        if ticker:
            por_ticker.setdefault(ticker, []).append(op)

    linhas = []
    for ticker, ops in por_ticker.items():
        ultimas = ultima_por_casa(ops, referencia)
        if not ultimas:
            continue
        contagem = {"compra": 0, "neutro": 0, "venda": 0}
        alvos = []
        mais_recente = None
        mais_recente_data = None
        for op in ultimas.values():
            contagem[_classe_recomendacao(op.get("recomendacao"))] += 1
            alvo = ler_preco_alvo(op.get("preco_alvo"))
            if alvo is not None:
                alvos.append(alvo)
            data_op = ler_data(op.get("data_materia"))
            if data_op is None:  # pragma: no cover - ultima_por_casa já filtrou
                continue
            if mais_recente_data is None or data_op > mais_recente_data:
                mais_recente, mais_recente_data = op, data_op
        na_janela = []
        for op in ops:
            data_op = ler_data(op.get("data_materia"))
            if data_op is not None and data_op >= limite:
                na_janela.append((data_op, op))
        na_janela.sort(key=lambda par: par[0], reverse=True)
        linhas.append(
            {
                "ticker": ticker,
                "contagem": contagem,
                "opinioes_texto": " · ".join(
                    f"{contagem[chave]} {rotulo}"
                    for chave, rotulo in _ROTULOS_CONTAGEM
                    if contagem[chave]
                ),
                "cobertura_insuficiente": calcular_consenso(ops, referencia)["consenso"]
                == "cobertura insuficiente",
                "alvo_min": min(alvos) if alvos else None,
                "alvo_max": max(alvos) if alvos else None,
                "mais_recente_data": mais_recente_data,
                "mais_recente_casa": (mais_recente or {}).get("casa"),
                "opinioes": [
                    {
                        **op,
                        "alvo_situacao": situacao_do_alvo(
                            op, fechamentos.get(ticker, [])
                        ),
                    }
                    for _, op in na_janela
                ],
            }
        )
    linhas.sort(key=lambda linha: linha["ticker"])
    linhas.sort(key=lambda linha: linha["mais_recente_data"], reverse=True)
    return linhas


def calcular_consenso(opinioes, referencia: datetime | None = None):
    if not opinioes:
        return {
            "consenso": "cobertura insuficiente",
            "preco_alvo_mediano": None,
            "faixa": None,
            "potencial": None,
            "detalhes": {},
        }
    casas = {
        casa: {
            "recomendacao": op["recomendacao"],
            "preco_alvo": op["preco_alvo"],
            "data": ler_data(op.get("data_materia")),
        }
        for casa, op in ultima_por_casa(opinioes, referencia).items()
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
