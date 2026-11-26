"""Os 20 radares da aba Alertas: com alertas, sem alertas, desatualizado ou indisponível (spec 150).

Cada radar aparece uma vez na aba: como card com alertas ou como nome na seção
"Sem alertas". A classificação segue a ordem da spec: payload ausente é
indisponível; coleta mais velha que o TTL durante o pregão é desatualizada;
lista vazia é "sem alertas"; o resto é card com alertas.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any

from app.services import carimbo

# (chave no contexto do template, título do card, campo da lista)
RADARES: tuple[tuple[str, str, str], ...] = (
    ("volume_alerts", "Radar de volume", "alerts"),
    ("variacao_subita", "Variação Súbita", "alertas"),
    ("concentracao_ordens", "Concentração de Ordens", "alertas"),
    ("exaustao_alta", "Exaustão de Alta", "alertas"),
    ("exaustao_queda", "Exaustão de Queda", "alertas"),
    ("exaustao_tendencia", "Exaustão de Tendência", "alertas"),
    ("radar_absorcao_cruzada", "Radar de Absorção Cruzada", "alertas"),
    ("liquidez_abertura", "Radar de Liquidez", "alertas"),
    ("radar_congestionamento", "Radar de Congestionamento", "alertas"),
    ("faca_caindo", "Radar de Faca Caindo", "alertas"),
    ("anomalias_spread", "Anomalias de Spread", "alertas"),
    ("short_squeeze", "Radar de Short Squeeze", "alertas"),
    ("falso_rompimento", "Falso Rompimento", "alertas"),
    ("radar_divergencia_volume", "Divergência Volume/Preço", "alertas"),
    ("esforco_resultado", "Índice de Esforço vs Resultado", "alertas"),
    ("scanner_capitulacao", "Scanner de Capitulação", "alertas"),
    ("armadilha_abertura", "Armadilhas de Abertura", "alertas"),
    ("compradores_fundo", "Compradores de Fundo", "alertas"),
    ("radar_anomalia_fechamento", "Radar de Anomalia de Fechamento", "alertas"),
    ("radar_inflexao", "Radar de Inflexão", "alertas"),
)

# Chaves de RADARES cujo snapshot tem outro nome (spec 166); as outras usam a própria chave.
SNAPSHOT_DO_RADAR: dict[str, str] = {"short_squeeze": "radar_short_squeeze"}


def escondidos(payloads: dict[str, Any]) -> list[str]:
    """Chaves de RADARES que a aba Alertas esconderia, na ordem declarada (spec 166).

    Recebe os payloads crus de `ler_snapshot`, indexados pela chave de RADARES.
    Escondido: payload ausente ou falso, `<campo>_json` ausente, que não é texto
    ou não é JSON válido, ou JSON falso (lista vazia, `null`). Não olha horário.
    """
    resultado: list[str] = []
    for chave, _nome, campo in RADARES:
        payload = payloads.get(chave)
        bruto = payload.get(f"{campo}_json") if isinstance(payload, dict) else None
        lista: Any = None
        if payload and isinstance(bruto, str):
            try:
                lista = json.loads(bruto)
            except ValueError:
                lista = None
        if not lista:
            resultado.append(chave)
    return resultado


COM_ALERTAS = "com_alertas"
SEM_ALERTAS = "sem_alertas"
DESATUALIZADO = "desatualizado"
INDISPONIVEL = "indisponivel"

_CLASSE_BASE = "visao-micro alertas"


def _campo(payload: Any, nome: str) -> Any:
    if isinstance(payload, dict):
        return payload.get(nome)
    return getattr(payload, nome, None)


def classificar(
    payload: Any, chave: str, agora: datetime, is_historical: bool
) -> tuple[str, datetime | None]:
    """Estado do radar e o horário bruto da coleta (quando existe)."""
    if not payload:
        return INDISPONIVEL, None
    timestamp = _campo(payload, "timestamp")
    if not isinstance(timestamp, datetime):
        timestamp = None
    if not is_historical and carimbo.desatualizado(timestamp, agora, chave):
        return DESATUALIZADO, timestamp
    if not _campo(payload, campo_da(chave)):
        return SEM_ALERTAS, timestamp
    return COM_ALERTAS, timestamp


def campo_da(chave: str) -> str:
    for c, _nome, campo in RADARES:
        if c == chave:
            return campo
    raise KeyError(chave)


def _hora(timestamp: datetime | None) -> str:
    if timestamp is None:
        return ""
    return carimbo.formatar(timestamp)[11:16]


JANELA_ULTIMO_ALERTA = 20
# Spec 199: "raro" é o radar que passou metade da janela sem acender, contado
# só depois de 10 pregões anteriores com registro.
LIMIAR_RARO = 10
MINIMO_REGISTROS_RARO = 10
MAX_LINHAS_RARO = 2


def janela_pregoes(agora: datetime, n: int = JANELA_ULTIMO_ALERTA) -> list[date]:
    """Os `n` pregões que terminam no corrente, do mais novo ao mais antigo (spec 185).

    Começa em `pregao_corrente`, não em `ultimo_pregao_fechado`: durante o
    pregão o dia corrente é a posição 0 ("mais cedo neste pregão").
    """
    from app.calendario import pregao_anterior, pregao_corrente

    if n <= 0:
        return []
    datas = [pregao_corrente(agora)]
    while len(datas) < n:
        datas.append(pregao_anterior(datas[-1]))
    return datas


def _rodadas(payload: Any) -> int:
    """`radares_pregao` do payload, ou 0 quando o pregão não tem registro."""
    if not isinstance(payload, dict):
        return 0
    r = payload.get("radares_pregao")
    if isinstance(r, bool) or not isinstance(r, int) or r <= 0:
        return 0
    return r


def ultimo_alerta(historico: dict[date, Any], pregoes: list[date]) -> dict[str, Any]:
    """Pregão mais recente da janela em que cada radar acendeu (spec 185).

    `historico` são os payloads `instrumentacao` por data; `pregoes` vai do
    mais novo ao mais antigo. Um radar acendeu num pregão com registro quando
    ficou escondido em menos rodadas do que as contadas.
    """
    registrados = 0
    resultado: dict[str, dict[str, Any]] = {
        chave: {"ultimo": None, "pregoes_atras": None} for chave, _n, _c in RADARES
    }
    for posicao, dia in enumerate(pregoes):
        payload = historico.get(dia)
        rodadas = _rodadas(payload)
        if not rodadas or not isinstance(payload, dict):
            continue
        registrados += 1
        escondidos_dia = payload.get("escondidos_pregao")
        if not isinstance(escondidos_dia, dict):
            escondidos_dia = {}
        for chave, info in resultado.items():
            if info["ultimo"] is not None:
                continue
            vezes = escondidos_dia.get(chave, 0)
            if isinstance(vezes, bool) or not isinstance(vezes, int):
                vezes = 0
            if vezes < rodadas:
                info["ultimo"] = dia
                info["pregoes_atras"] = posicao
    return {"janela": len(pregoes), "registrados": registrados, "radares": resultado}


def ultimo_alerta_vazio(janela: int = JANELA_ULTIMO_ALERTA) -> dict[str, Any]:
    """O resultado sem nenhum registro: data histórica ou leitura falha."""
    return {
        **ultimo_alerta({}, []),
        "janela": janela,
        "anterior": {**ultimo_alerta({}, []), "janela": janela - 1},
    }


def frase_ultimo_alerta(chave: str, ultimo: dict[str, Any] | None) -> str:
    """A frase depois do nome na seção "Sem alertas"; vazia sem registro."""
    if not ultimo or not ultimo.get("registrados"):
        return ""
    info = ultimo["radares"].get(chave) or {}
    atras = info.get("pregoes_atras")
    if atras == 0:
        return "· teve alerta mais cedo neste pregão"
    if atras is not None:
        dia = info["ultimo"]
        unidade = "pregão" if atras == 1 else "pregões"
        return f"· último alerta há {atras} {unidade} ({dia.strftime('%d/%m')})"
    m = ultimo["registrados"]
    if m == 1:
        return "· sem alerta no 1 pregão registrado"
    return f"· sem alerta nos {m} pregões registrados"


def radares_raros(
    estados: dict[str, str], anterior: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """Radares acesos agora que quase nunca acendem (spec 199).

    `estados` é o estado de `classificar` por chave de RADARES; `anterior` é
    `ultimo_alerta(historico, pregoes[1:])`, sem o pregão corrente. Devolve
    `{"chave", "nome", "ultimo", "pregoes_atras"}`, o maior intervalo primeiro
    (`pregoes_atras` None antes de qualquer N); `pregoes_atras` já conta o
    pregão corrente (1 é o pregão anterior).
    """
    if not anterior or anterior.get("registrados", 0) < MINIMO_REGISTROS_RARO:
        return []
    raros: list[tuple[int, int, dict[str, Any]]] = []
    for ordem, (chave, nome, _campo_lista) in enumerate(RADARES):
        if estados.get(chave) != COM_ALERTAS:
            continue
        info = (anterior.get("radares") or {}).get(chave) or {}
        atras = info.get("pregoes_atras")
        if atras is None:
            item = {"chave": chave, "nome": nome, "ultimo": None, "pregoes_atras": None}
            raros.append((-JANELA_ULTIMO_ALERTA - 1, ordem, item))
            continue
        n = atras + 1
        if n < LIMIAR_RARO:
            continue
        item = {
            "chave": chave,
            "nome": nome,
            "ultimo": info["ultimo"],
            "pregoes_atras": n,
        }
        raros.append((-n, ordem, item))
    raros.sort(key=lambda t: (t[0], t[1]))
    return [item for _peso, _ordem, item in raros]


def frases_raros(raros: list[dict[str, Any]], registrados_antes: int) -> list[str]:
    """As linhas sob a manchete: no máximo duas, mais a do excedente (spec 199)."""
    linhas: list[str] = []
    for item in raros[:MAX_LINHAS_RARO]:
        atras = item["pregoes_atras"]
        if atras is None:
            linhas.append(
                f"{item['nome']} acendeu: nenhum alerta nos {registrados_antes} "
                "pregões registrados antes deste."
            )
        else:
            linhas.append(
                f"{item['nome']} acendeu: o último alerta foi há {atras} pregões "
                f"({item['ultimo'].strftime('%d/%m')})."
            )
    resto = len(raros) - MAX_LINHAS_RARO
    if resto == 1:
        linhas.append("e mais 1 radar raro acendeu; veja a aba Alertas.")
    elif resto > 1:
        linhas.append(f"e mais {resto} radares raros acenderam; veja a aba Alertas.")
    return linhas


def raros_do_contexto(
    payloads: dict[str, Any],
    agora: datetime,
    is_historical: bool,
    ultimo: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Os raros a partir dos payloads dos radares e do resultado da rota (spec 199)."""
    if is_historical or not ultimo:
        return []
    estados = {
        chave: classificar(payloads.get(chave), chave, agora, is_historical)[0]
        for chave, _n, _c in RADARES
    }
    return radares_raros(estados, ultimo.get("anterior"))


def raros_api(raros: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """`paineis.radares_ultimo_alerta.raros` do `/api/snapshot`, com datas ISO."""
    return [
        {
            **item,
            "ultimo": item["ultimo"].isoformat() if item["ultimo"] else None,
        }
        for item in raros
    ]


def registrados_antes(ultimo: dict[str, Any] | None) -> int:
    anterior = (ultimo or {}).get("anterior") or {}
    return int(anterior.get("registrados") or 0)


def ultimo_alerta_api(ultimo: dict[str, Any]) -> dict[str, Any]:
    """`paineis.radares_ultimo_alerta` do `/api/snapshot`, com datas ISO."""
    return {
        "janela": ultimo["janela"],
        "registrados": ultimo["registrados"],
        "radares": {
            chave: {
                "ultimo": info["ultimo"].isoformat() if info["ultimo"] else None,
                "pregoes_atras": info["pregoes_atras"],
            }
            for chave, info in ultimo["radares"].items()
        },
    }


def resumo(
    contexto: dict[str, Any],
    agora: datetime,
    is_historical: bool,
    mostrar_vazios: bool,
    ultimo: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """O que a aba Alertas precisa: a classe de cada card e a seção "Sem alertas".

    Cada item de `sem_alertas` é `{"nome", "frase"}`; a frase do último alerta
    (spec 185) só aparece fora de data histórica.
    """
    classes: dict[str, str] = {}
    sem_alertas: list[dict[str, str]] = []
    outros: list[dict[str, str]] = []
    for chave, nome, _campo_lista in RADARES:
        estado, timestamp = classificar(
            contexto.get(chave), chave, agora, is_historical
        )
        if estado == COM_ALERTAS:
            classes[chave] = _CLASSE_BASE
        elif estado == SEM_ALERTAS:
            frase = "" if is_historical else frase_ultimo_alerta(chave, ultimo)
            sem_alertas.append({"nome": nome, "frase": frase})
            classes[chave] = f"{_CLASSE_BASE} radar-vazio" + (
                "" if mostrar_vazios else " escondido"
            )
        elif estado == DESATUALIZADO:
            outros.append({"nome": nome, "estado": estado, "hora": _hora(timestamp)})
            classes[chave] = f"{_CLASSE_BASE} escondido"
        else:
            outros.append({"nome": nome, "estado": estado, "hora": ""})
            classes[chave] = f"{_CLASSE_BASE} escondido"
    return {
        "classes": classes,
        "sem_alertas": sem_alertas,
        "outros": outros,
        "mostrar_vazios": mostrar_vazios,
        "secao": bool(sem_alertas or outros),
    }


MINIMO_CONFLUENCIA = 2
MAX_LINHAS_CONFLUENCIA = 10


def _ticker(item: Any) -> str | None:
    """Ticker normalizado: sem espaços, maiúsculo, sem o sufixo `.SA`."""
    bruto = _campo(item, "ticker")
    if not isinstance(bruto, str):
        return None
    ticker = bruto.strip().upper()
    if ticker.endswith(".SA"):
        ticker = ticker[:-3]
    return ticker or None


def _utc(ts: datetime) -> datetime:
    return ts if ts.tzinfo is not None else ts.replace(tzinfo=timezone.utc)


def _texto_excedentes(resto: list[dict[str, Any]]) -> str:
    """`+N ações em K radares` para as linhas que passam do limite."""
    if not resto:
        return ""
    contagens = sorted({len(linha["radares"]) for linha in resto})
    radares = (
        f"{contagens[0]} radares"
        if len(contagens) == 1
        else f"{contagens[0]} a {contagens[-1]} radares"
    )
    acoes = "ação" if len(resto) == 1 else "ações"
    return f"+{len(resto)} {acoes} em {radares}"


def confluencia(
    contexto: dict[str, Any],
    agora: datetime,
    is_historical: bool,
    limite: int | None = MAX_LINHAS_CONFLUENCIA,
) -> dict[str, Any]:
    """As ações citadas por 2 ou mais radares com coleta em dia (spec 155).

    Conta citações; não pesa radares nem recomenda. Radar desatualizado ou
    indisponível fica fora da contagem e de `lidos`. Com `limite=None`, todas
    as linhas vão em `acoes` (registro do pregão, spec 186).
    """
    citacoes: dict[str, list[str]] = {}
    horarios: dict[str, datetime | None] = {}
    lidos = 0
    for chave, nome, campo in RADARES:
        payload = contexto.get(chave)
        estado, ts = classificar(payload, chave, agora, is_historical)
        if estado in (COM_ALERTAS, SEM_ALERTAS):
            lidos += 1
        if estado != COM_ALERTAS:
            continue
        horarios[nome] = ts
        tickers = {_ticker(item) for item in (_campo(payload, campo) or [])}
        for ticker in tickers:
            if ticker:
                citacoes.setdefault(ticker, []).append(nome)

    linhas = sorted(
        (
            {"ticker": ticker, "radares": nomes}
            for ticker, nomes in citacoes.items()
            if len(nomes) >= MINIMO_CONFLUENCIA
        ),
        key=lambda linha: (-len(linha["radares"]), linha["ticker"]),
    )
    citados = {nome for linha in linhas for nome in linha["radares"]}
    carimbos = [_utc(ts) for nome in citados if (ts := horarios.get(nome))]
    corte = len(linhas) if limite is None else limite
    resto = linhas[corte:]
    return {
        "acoes": linhas[:corte],
        "excedentes": len(resto),
        "texto_excedentes": _texto_excedentes(resto),
        "lidos": lidos,
        "horario": min(carimbos) if carimbos else None,
        "horario_texto": carimbo.formatar(min(carimbos)) if carimbos else "",
    }


MAXIMO_REGISTROS = 252


def registro_do_pregao(payloads: dict[str, Any], data: date) -> dict[str, Any] | None:
    """A confluência de um pregão fechado, para guardar (spec 186).

    `None` quando nenhum radar foi lido: pregão sem leitura não é pregão sem
    confluência. Com `is_historical=True`, o `agora` não pesa no resultado.
    """
    resultado = confluencia(
        payloads, datetime.now(timezone.utc), is_historical=True, limite=None
    )
    if not resultado["lidos"]:
        return None
    return {
        "data": data.isoformat(),
        "lidos": resultado["lidos"],
        "acoes": [
            {"ticker": linha["ticker"], "radares": list(linha["radares"])}
            for linha in resultado["acoes"]
        ],
    }


def acumular(
    anterior: list[dict[str, Any]],
    novos: list[dict[str, Any]],
    maximo: int = MAXIMO_REGISTROS,
) -> list[dict[str, Any]]:
    """Um registro por data (o de `novos` vence), crescente, só os `maximo` mais recentes."""
    por_data = {r["data"]: r for r in anterior}
    por_data.update({r["data"]: r for r in novos})
    ordenados = [por_data[d] for d in sorted(por_data)]
    return ordenados[-maximo:] if maximo > 0 else []


def memoria_confluencia(snapshot: Any) -> dict[str, Any] | None:
    """`{"pregoes", "de", "ate", "ultimo", "coletado_em"}` do snapshot, ou None (spec 186)."""
    if not isinstance(snapshot, dict):
        return None
    registros = snapshot.get("registros")
    if not isinstance(registros, list) or not registros:
        return None
    return {
        "pregoes": len(registros),
        "de": snapshot.get("de") or registros[0].get("data"),
        "ate": snapshot.get("ate") or registros[-1].get("data"),
        "ultimo": registros[-1],
        "coletado_em": snapshot.get("coletado_em"),
    }


def frase_memoria(memoria: dict[str, Any] | None) -> str:
    """ "Guardada a cada fechamento: N pregões, desde DD/MM/AAAA."; vazia sem memória."""
    if not memoria:
        return ""
    try:
        desde = date.fromisoformat(str(memoria["de"])).strftime("%d/%m/%Y")
    except ValueError:
        return ""
    n = memoria["pregoes"]
    unidade = "pregão" if n == 1 else "pregões"
    return f"Guardada a cada fechamento: {n} {unidade}, desde {desde}."
