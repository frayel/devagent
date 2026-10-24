from app.services.consultor_opinioes import extrair_opinioes
import logging
import time
import httpx
import xml.etree.ElementTree as ET
from app.consultor.pre_filtro import filtrar_materia
from app.consultor.armazenamento import save_materia

logger = logging.getLogger(__name__)

FEEDS = ["https://www.moneytimes.com.br/feed/", "https://www.infomoney.com.br/feed/"]

HEADERS = {"User-Agent": "Consultor/1.0 (+https://github.com/agent/coleta)"}


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
    for i in range(max_retries):
        try:
            resp = httpx.get(url, headers=HEADERS, timeout=10, follow_redirects=True)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            if i == max_retries - 1:
                logger.error(
                    f"Falha ao buscar {url} após {max_retries} tentativas: {e}"
                )
                return None
            time.sleep(2**i)
    return None


def collect_and_save() -> bool:
    sucesso = False
    for url in FEEDS:
        xml_content = fetch_with_retry(url)
        if xml_content:
            sucesso = True
            materias = parse_feed(xml_content)
            for mat in materias:
                tickers = filtrar_materia(
                    mat["titulo"], mat["descricao"], mat["conteudo"]
                )
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
        time.sleep(2)
    extrair_opinioes()
    return sucesso
