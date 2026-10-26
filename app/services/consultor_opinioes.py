import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
import httpx

from app.consultor.armazenamento import get_connection
from app.consultor.universo import CARTEIRA_IBOVESPA
from app.consultor.pre_filtro import normalizar
from app.collectors import registro_fontes
from app.services import gemini_modelo

logger = logging.getLogger(__name__)

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
GEMINI_MAX_CHAMADAS = 200
PAUSA_5XX = 5.0


def sql_para(backend: str, sqlite_sql: str) -> str:
    if backend == "postgres":
        return sqlite_sql.replace("?", "%s")
    return sqlite_sql


def get_llm_uso_hoje() -> int:
    conn, backend = get_connection()
    try:
        now_brt = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-3)))
        hoje = now_brt.date().isoformat()
        cursor = conn.cursor()
        cursor.execute(
            sql_para(backend, "SELECT chamadas FROM consultor_llm_uso WHERE data = ?"),
            (hoje,),
        )
        row = cursor.fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


def incrementar_llm_uso() -> None:
    conn, backend = get_connection()
    try:
        now_brt = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-3)))
        hoje = now_brt.date().isoformat()
        cursor = conn.cursor()
        if backend == "postgres":
            cursor.execute(
                "INSERT INTO consultor_llm_uso (data, chamadas) VALUES (%s, 1) ON CONFLICT (data) DO UPDATE SET chamadas = consultor_llm_uso.chamadas + 1",
                (hoje,),
            )
        else:
            cursor.execute(
                "INSERT OR REPLACE INTO consultor_llm_uso (data, chamadas) VALUES (?, COALESCE((SELECT chamadas FROM consultor_llm_uso WHERE data = ?), 0) + 1)",
                (hoje, hoje),
            )
        conn.commit()
    finally:
        conn.close()


def set_opinioes_status(
    status: str, motivo: str = "", descartadas_na_rodada: int = 0
) -> None:
    conn, backend = get_connection()
    try:
        agora = datetime.now(timezone.utc).isoformat()
        cur = conn.cursor()

        # Pegar descartadas antigas e somar
        cur.execute("SELECT descartadas FROM consultor_opinioes_status LIMIT 1")
        row = cur.fetchone()
        descartadas_antigas = row[0] if row and row[0] else 0
        descartadas_total = descartadas_antigas + descartadas_na_rodada

        # Calcular os novos valores
        sete_dias = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        cur.execute(
            sql_para(
                backend,
                "SELECT COUNT(*) FROM consultor_opinioes WHERE extraida_em >= ?",
            ),
            (sete_dias,),
        )
        op_gravadas = cur.fetchone()[0]

        vinte_e_quatro_h = (
            datetime.now(timezone.utc) - timedelta(hours=24)
        ).isoformat()
        cur.execute(
            sql_para(
                backend,
                "SELECT COUNT(*) FROM consultor_fila_materias WHERE processada = 1 AND criado_em >= ?",
            ),
            (vinte_e_quatro_h,),
        )
        mat_processadas = cur.fetchone()[0]

        cur.execute("DELETE FROM consultor_opinioes_status")
        cur.execute(
            sql_para(
                backend,
                "INSERT INTO consultor_opinioes_status (status, motivo, desde, ultima_extracao_em, materias_processadas, opinioes_gravadas, descartadas) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ),
            (
                status,
                motivo,
                agora,
                agora,
                mat_processadas,
                op_gravadas,
                descartadas_total,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_materias_nao_processadas() -> list[dict]:
    conn, backend = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT guid, titulo, descricao, conteudo, data_publicacao, link, tickers_citados, criado_em FROM consultor_fila_materias WHERE processada = 0 ORDER BY criado_em ASC LIMIT 10"
        )
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append(
                {
                    "guid": row[0],
                    "titulo": row[1],
                    "descricao": row[2],
                    "conteudo": row[3],
                    "data_publicacao": row[4],
                    "link": row[5],
                    "tickers_citados": json.loads(row[6]),
                    "criado_em": row[7],
                }
            )
        return result
    finally:
        conn.close()


def marcar_como_processada(guid: str) -> None:
    conn, backend = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            sql_para(
                backend,
                "UPDATE consultor_fila_materias SET processada = 1 WHERE guid = ?",
            ),
            (guid,),
        )
        conn.commit()
    finally:
        conn.close()


def save_opiniao(
    guid: str,
    ticker: str,
    casa: str,
    recomendacao: str,
    preco_alvo: float | None,
    resumo: str,
    trecho: str,
    data_materia: str,
    link: str,
) -> None:
    conn, backend = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            sql_para(
                backend,
                "SELECT id FROM consultor_opinioes WHERE ticker = ? AND casa = ? AND recomendacao = ? AND data_materia LIKE ?",
            ),
            (ticker, casa, recomendacao, f"{data_materia[:10]}%"),
        )
        if cur.fetchone():
            return

        if backend == "postgres":
            cur.execute(
                """
                INSERT INTO consultor_opinioes
                (guid, ticker, casa, recomendacao, preco_alvo, resumo, trecho, data_materia, link)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker, casa, recomendacao, data_materia) DO NOTHING
                """,
                (
                    guid,
                    ticker,
                    casa,
                    recomendacao,
                    str(preco_alvo) if preco_alvo else "",
                    resumo,
                    trecho,
                    data_materia,
                    link,
                ),
            )
        else:
            cur.execute(
                """
                INSERT OR IGNORE INTO consultor_opinioes
                (guid, ticker, casa, recomendacao, preco_alvo, resumo, trecho, data_materia, link)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    guid,
                    ticker,
                    casa,
                    recomendacao,
                    str(preco_alvo) if preco_alvo else "",
                    resumo,
                    trecho,
                    data_materia,
                    link,
                ),
            )
        conn.commit()
    except Exception as e:
        print(f"Error in save_opiniao: {e}")
    finally:
        conn.close()


def normalizar_recomendacao(rec: str) -> str:
    if not rec:
        return "neutro"
    rec = str(rec).lower().strip()
    if rec in ["compra", "outperform", "overweight"]:
        return "compra"
    if rec in ["venda", "underperform", "underweight"]:
        return "venda"
    return "neutro"


def _gerar(api_key: str, payload: dict) -> httpx.Response:
    """Chama o generateContent no modelo da vez e registra o resultado.

    Um 404 quer dizer que o modelo foi aposentado: descarta, descobre outro
    e tenta mais uma vez.
    """
    forcar = False
    for tentativa in range(2):
        modelo = gemini_modelo.modelo_atual(api_key, forcar=forcar)
        resp = httpx.post(
            GEMINI_URL.format(model=modelo),
            headers={"x-goog-api-key": api_key},
            json=payload,
            timeout=30.0,
        )
        if resp.status_code == 200:
            registro_fontes.sucesso(
                gemini_modelo.FONTE,
                url="https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
            )
            return resp
        registro_fontes.falha(
            gemini_modelo.FONTE,
            f"HTTP {resp.status_code} no modelo {modelo}",
            grave=registro_fontes.grave(resp.status_code),
        )
        if resp.status_code >= 500 and tentativa == 0:
            # 503 é o modelo sobrecarregado: costuma passar em segundos.
            time.sleep(PAUSA_5XX)
            continue
        if resp.status_code != 404 or not gemini_modelo.descartar(modelo):
            return resp
        logger.warning(f"Modelo Gemini {modelo} não existe mais; buscando outro")
        forcar = True
    return resp


def extrair_opinioes():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        try:
            set_opinioes_status("sem_chave", "sem chave configurada")
        except Exception as e:
            logger.error(f"Erro ao gravar status: {e}")
        return

    max_calls = int(os.environ.get("GEMINI_MAX_CHAMADAS_DIA", GEMINI_MAX_CHAMADAS))

    try:
        usos = get_llm_uso_hoje()
        if usos >= max_calls:
            set_opinioes_status("cota", "cota do LLM esgotada")
            return

        materias = get_materias_nao_processadas()
    except Exception as e:
        logger.error(f"Falha de banco antes da extracao: {e}")
        try:
            set_opinioes_status("erro", f"falha no banco: {type(e).__name__}")
        except Exception as set_err:
            logger.error(f"Erro ao gravar status de falha no banco: {set_err}")
        return

    if not materias:
        # Se estava com erro/timeout antes, mantemos. Senão, se tem feeds e tá tudo ok, não mexemos.
        return

    materias_texto = []
    for i, m in enumerate(materias):
        materias_texto.append(
            f"Materia {i + 1} (ID: {m['guid']}):\nTitulo: {m['titulo']}\nDescricao: {m['descricao']}\nConteudo: {m['conteudo']}\nTickers citados: {', '.join(m['tickers_citados'])}\n\n"
        )

    prompt = f"""
    Extraia as opiniões e recomendações de casas de análise sobre os tickers informados nas seguintes matérias.
    Só extraia opiniões para os tickers da lista: {", ".join(CARTEIRA_IBOVESPA)}. Não invente dados ou campos.
    Responda apenas com a lista JSON seguindo o esquema.

    Textos:
    {"".join(materias_texto)}
    """

    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "id_materia": {"type": "string"},
                "ticker": {"type": "string"},
                "casa": {"type": "string"},
                "recomendacao": {"type": "string"},
                "preco_alvo": {"type": "string"},
                "resumo": {"type": "string"},
                "trecho": {"type": "string"},
            },
            "required": [
                "id_materia",
                "ticker",
                "casa",
                "recomendacao",
                "resumo",
                "trecho",
            ],
        },
    }

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": schema,
        },
    }

    try:
        resp = _gerar(api_key, payload)

        if resp.status_code == 429:
            set_opinioes_status("cota", "cota do LLM esgotada")
            return
        elif resp.status_code != 200:
            set_opinioes_status("erro", f"LLM fora do ar (HTTP {resp.status_code})")
            return

        incrementar_llm_uso()
        data = resp.json()

        try:
            content_text = data["candidates"][0]["content"]["parts"][0]["text"]
            opinioes = json.loads(content_text)
        except Exception:
            set_opinioes_status("invalido", "resposta inválida do LLM")
            return

        for op in opinioes:
            guid = op.get("id_materia")
            materia = next((m for m in materias if m["guid"] == guid), None)
            if not materia:
                continue

            ticker = op.get("ticker", "").upper()
            if ticker not in CARTEIRA_IBOVESPA:
                continue

            casa = op.get("casa", "").strip()
            if not casa:
                continue

            recomendacao = normalizar_recomendacao(op.get("recomendacao", ""))
            preco_alvo = op.get("preco_alvo")
            resumo = op.get("resumo", "").strip()[:120]
            trecho = op.get("trecho", "").strip()

            # Validation: preco_alvo must appear in the text if present
            texto_completo = normalizar(
                f"{materia['titulo']} {materia['descricao']} {materia['conteudo']}"
            )

            if preco_alvo:
                # remove spaces or R$ to check existence roughly, or just check digits
                import re

                digitos_alvo = re.findall(r"\d+", preco_alvo)
                if not digitos_alvo or not any(
                    d in texto_completo for d in digitos_alvo
                ):
                    # For simplicity, if we can't find the numbers, it's alvo_ausente
                    continue

            if normalizar(trecho) not in texto_completo:
                continue

            save_opiniao(
                guid=materia["guid"],
                ticker=ticker,
                casa=casa,
                recomendacao=recomendacao,
                preco_alvo=preco_alvo if preco_alvo else None,
                resumo=resumo,
                trecho=trecho,
                data_materia=materia["data_publicacao"] or materia["criado_em"],
                link=materia["link"],
            )

        # Mark all processed
        for m in materias:
            marcar_como_processada(m["guid"])

        set_opinioes_status("ok", "")

    except httpx.TimeoutException:
        registro_fontes.falha(gemini_modelo.FONTE, "timeout na geração")
        set_opinioes_status("erro", "LLM timeout")
    except httpx.RequestError as e:
        registro_fontes.falha(gemini_modelo.FONTE, f"{type(e).__name__} na geração")
        set_opinioes_status("erro", "LLM fora do ar (rede)")
    except Exception as e:
        logger.error(f"Erro ao extrair opinioes: {e}")
        set_opinioes_status("erro", "erro interno ao consultar LLM")
