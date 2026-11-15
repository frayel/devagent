from app.services.consultor_opinioes import extrair_opinioes
import html
import logging
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
import xml.etree.ElementTree as ET
from app.collectors import registro_fontes
from app.consultor.pre_filtro import filtrar_materia
from app.consultor.armazenamento import (
    get_telegram_cursor,
    save_materia,
    set_telegram_cursor,
)

logger = logging.getLogger(__name__)

FEEDS = ["https://www.moneytimes.com.br/feed/", "https://www.infomoney.com.br/feed/"]

HEADERS = {"User-Agent": "Consultor/1.0 (+https://github.com/agent/coleta)"}

NOMES_FEEDS = {
    "https://www.moneytimes.com.br/feed/": "Money Times",
    "https://www.infomoney.com.br/feed/": "InfoMoney",
}

# Canais públicos do Telegram (spec 157). A chave é o nome na URL `t.me/<canal>`.
TELEGRAM_CANAIS = {
    "clubeacionista": "Clube Acionista",
    "RepositorioDeAcoes": "Repositório de Ações",
    "universoantifragil": "Universo Antifrágil",
}
# Canais com prévia pública em `t.me/s/<canal>`; os outros são lidos por ID.
TELEGRAM_PREVIA = ("clubeacionista",)
# Ponto de partida dos canais lidos por ID, na primeira rodada (IDs de 04/11/2026).
TELEGRAM_INICIO = {"RepositorioDeAcoes": 159281, "universoantifragil": 3549}
TELEGRAM_MAX_PAGINAS = 5
TELEGRAM_MAX_IDS = 30
TELEGRAM_VAZIOS_FIM = 3
PAUSA_TELEGRAM = 2.0

# Resultado da última tentativa de cada fonte, na memória do processo:
# url -> {"status": "ok" | "falha", "ultima_coleta": ISO UTC}.
_ultima_tentativa: dict[str, dict[str, str]] = {}


def url_do_canal(canal: str) -> str:
    return f"https://t.me/{canal}"


def _marcar_tentativa(url: str, ok: bool) -> None:
    _ultima_tentativa[url] = {
        "status": "ok" if ok else "falha",
        "ultima_coleta": datetime.now(timezone.utc).isoformat(),
    }


def limpar_status_fontes() -> None:
    _ultima_tentativa.clear()


def status_fontes() -> list[dict[str, str]]:
    """As fontes de opinião com o resultado real da última tentativa."""
    fontes = [(url, nome) for url, nome in NOMES_FEEDS.items()]
    fontes += [
        (url_do_canal(canal), f"Telegram · {nome}")
        for canal, nome in TELEGRAM_CANAIS.items()
    ]
    saida = []
    for url, nome in fontes:
        t = _ultima_tentativa.get(url, {"status": "sem coleta", "ultima_coleta": ""})
        saida.append(
            {
                "url": url,
                "nome": nome,
                "status": t["status"],
                "ultima_coleta": t["ultima_coleta"],
            }
        )
    return saida


def origem_do_link(link: str | None) -> str:
    """De onde veio a matéria de uma opinião, pelo link gravado (coluna Via)."""
    if not link:
        return ""
    try:
        partes = urlparse(link)
    except ValueError:
        return ""
    dominio = (partes.hostname or "").lower()
    if dominio.startswith("www."):
        dominio = dominio[4:]
    if "moneytimes.com.br" in dominio:
        return "Money Times"
    if "infomoney.com.br" in dominio:
        return "InfoMoney"
    if dominio == "t.me":
        canal = partes.path.strip("/").split("/")[0]
        if canal == "s":
            canal = partes.path.strip("/").split("/")[1]
        nome = TELEGRAM_CANAIS.get(canal, canal)
        return f"Telegram · {nome}"
    return dominio


def parse_feed(xml_content: str) -> list[dict]:
    materias = []
    try:
        root = ET.fromstring(xml_content)
        for item in root.findall(".//item"):
            guid_elem = item.find("guid")
            link_elem = item.find("link")
            guid = (
                guid_elem.text
                if guid_elem is not None and guid_elem.text
                else (link_elem.text if link_elem is not None else None)
            )

            titulo_elem = item.find("title")
            titulo = titulo_elem.text if titulo_elem is not None else ""

            desc_elem = item.find("description")
            descricao = desc_elem.text if desc_elem is not None else ""

            pub_elem = item.find("pubDate")
            data_publicacao = pub_elem.text if pub_elem is not None else ""

            link = link_elem.text if link_elem is not None else ""

            conteudo = ""
            for child in item:
                if "content" in child.tag and "encoded" in child.tag:
                    conteudo = child.text if child.text else ""
                    break

            if guid:
                materias.append(
                    {
                        "guid": guid,
                        "titulo": titulo or "",
                        "descricao": descricao or "",
                        "conteudo": conteudo or "",
                        "data_publicacao": data_publicacao or "",
                        "link": link or "",
                    }
                )
    except Exception as e:
        logger.error(f"Erro ao fazer parse do XML: {e}")
    return materias


def fetch_with_retry(url: str, max_retries: int = 3) -> str | None:
    """Busca a URL com retry e anota o resultado final no `registro_fontes`."""
    nome = registro_fontes.nome_da_fonte(urlparse(url).hostname or "")
    for i in range(max_retries):
        try:
            resp = httpx.get(url, headers=HEADERS, timeout=10, follow_redirects=True)
            resp.raise_for_status()
            registro_fontes.sucesso(nome, url=url)
            return resp.text
        except Exception as e:
            if i == max_retries - 1:
                logger.error(
                    f"Falha ao buscar {url} após {max_retries} tentativas: {e}"
                )
                status = (
                    e.response.status_code
                    if isinstance(e, httpx.HTTPStatusError)
                    else None
                )
                registro_fontes.falha(
                    nome,
                    f"HTTP {status} em {url}"
                    if status
                    else f"{type(e).__name__} em {url}",
                    grave=registro_fontes.grave(status) if status else True,
                    url=url,
                    status=status,
                )
                return None
            time.sleep(2**i)
    return None


def _guardar(mat: dict) -> None:
    tickers = filtrar_materia(mat["titulo"], mat["descricao"], mat["conteudo"])
    if tickers:
        save_materia(
            mat["guid"],
            mat["titulo"],
            mat["descricao"],
            mat["conteudo"],
            mat["data_publicacao"],
            mat["link"],
            tickers,
        )


# --- Telegram (spec 157) -------------------------------------------------

_TAG = re.compile(r"<[^>]+>")
_BR = re.compile(r"<br\s*/?>", re.I)
_TIME = re.compile(r'<time[^>]*\bdatetime="([^"]+)"')
_POST = re.compile(r'data-post="([^"/]+)/(\d+)"')
_TEXTO = re.compile(
    r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', re.S
)
_OG_DESC = re.compile(r'<meta property="og:description" content="([^"]*)"', re.S)


def texto_sem_tags(trecho: str) -> str:
    return html.unescape(_TAG.sub("", _BR.sub("\n", trecho))).strip()


def materia_telegram(canal: str, msg_id: int, texto: str, data: str) -> dict:
    link = f"https://t.me/{canal}/{msg_id}"
    primeira = texto.split("\n", 1)[0].strip() if texto else ""
    return {
        "guid": link,
        "titulo": primeira[:200],
        "descricao": "",
        "conteudo": texto,
        "data_publicacao": data,
        "link": link,
        "id": msg_id,
    }


def parse_previa_telegram(html_previa: str) -> list[dict]:
    """Mensagens da prévia `t.me/s/<canal>`, na ordem da página."""
    materias = []
    inicios = list(_POST.finditer(html_previa))
    for i, m in enumerate(inicios):
        fim = inicios[i + 1].start() if i + 1 < len(inicios) else len(html_previa)
        bloco = html_previa[m.start() : fim]
        t = _TIME.search(bloco)
        if not t:
            continue
        txt = _TEXTO.search(bloco)
        texto = texto_sem_tags(txt.group(1)) if txt else ""
        materias.append(
            materia_telegram(m.group(1), int(m.group(2)), texto, t.group(1))
        )
    return materias


def data_do_widget(html_widget: str) -> str | None:
    t = _TIME.search(html_widget)
    return t.group(1) if t else None


def texto_do_post(html_post: str) -> str:
    m = _OG_DESC.search(html_post)
    return html.unescape(m.group(1)).strip() if m else ""


def _ler_previa(canal: str, cursor: int | None) -> tuple[list[dict], bool]:
    """Lê a prévia pública. Devolve as mensagens novas e se a leitura deu certo."""
    novas: dict[int, dict] = {}
    url = f"https://t.me/s/{canal}"
    for pagina in range(TELEGRAM_MAX_PAGINAS):
        if pagina:
            time.sleep(PAUSA_TELEGRAM)
        conteudo = fetch_with_retry(url)
        if conteudo is None:
            return [], False
        msgs = parse_previa_telegram(conteudo)
        if not msgs:
            break
        for mat in msgs:
            if cursor is None or mat["id"] > cursor:
                novas[mat["id"]] = mat
        menor = min(mat["id"] for mat in msgs)
        if cursor is None or menor <= cursor + 1:
            break
        url = f"https://t.me/s/{canal}?before={menor}"
    return [novas[k] for k in sorted(novas)], True


def _ler_por_id(canal: str, cursor: int | None) -> tuple[list[dict], bool]:
    """Lê post a post a partir do cursor (canais sem prévia pública)."""
    inicio = cursor if cursor is not None else TELEGRAM_INICIO[canal]
    lidas: list[dict] = []
    vazios = 0
    msg_id = inicio
    for n in range(TELEGRAM_MAX_IDS):
        msg_id = inicio + 1 + n
        if n:
            time.sleep(PAUSA_TELEGRAM)
        widget = fetch_with_retry(f"https://t.me/{canal}/{msg_id}?embed=1")
        if widget is None:
            return [], False
        data = data_do_widget(widget)
        if data is None:
            vazios += 1
            if vazios >= TELEGRAM_VAZIOS_FIM:
                logger.warning(
                    f"Telegram {canal}: {TELEGRAM_VAZIOS_FIM} IDs seguidos sem "
                    f"mensagem até {msg_id}; leitura encerrada nesta rodada"
                )
                break
            continue
        vazios = 0
        time.sleep(PAUSA_TELEGRAM)
        post = fetch_with_retry(f"https://t.me/{canal}/{msg_id}")
        if post is None:
            return [], False
        lidas.append(materia_telegram(canal, msg_id, texto_do_post(post), data))
    return lidas, True


def coletar_canal(canal: str) -> bool:
    """Lê um canal, guarda as matérias que passam no filtro e avança o cursor."""
    try:
        cursor = get_telegram_cursor(canal)
        if canal in TELEGRAM_PREVIA:
            materias, ok = _ler_previa(canal, cursor)
        else:
            materias, ok = _ler_por_id(canal, cursor)
        if ok:
            for mat in materias:
                _guardar(mat)
            ultimo = max([m["id"] for m in materias], default=cursor)
            if ultimo is None:
                ultimo = TELEGRAM_INICIO.get(canal)
            if ultimo is not None:
                set_telegram_cursor(canal, ultimo)
    except Exception as e:
        logger.error(f"Falha ao coletar o canal {canal} do Telegram: {e}")
        ok = False
    _marcar_tentativa(url_do_canal(canal), ok)
    return ok


def collect_and_save() -> bool:
    sucesso = False
    for url in FEEDS:
        xml_content = fetch_with_retry(url)
        _marcar_tentativa(url, xml_content is not None)
        if xml_content:
            sucesso = True
            for mat in parse_feed(xml_content):
                _guardar(mat)
        time.sleep(2)
    for canal in TELEGRAM_CANAIS:
        if coletar_canal(canal):
            sucesso = True
        time.sleep(PAUSA_TELEGRAM)
    extrair_opinioes()
    return sucesso
