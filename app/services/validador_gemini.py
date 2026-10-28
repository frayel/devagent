import asyncio
import logging
import os
from datetime import timedelta
import time

from app.services import gemini_modelo
import httpx

logger = logging.getLogger(__name__)

INTERVALO = timedelta(hours=6)


async def validar() -> None:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return

    logger.info("Validando chave do Gemini...")
    try:
        # Usa executor para rodar de forma síncrona, já que _listar_modelos usa httpx sem async
        await asyncio.to_thread(gemini_modelo._listar_modelos, api_key)
        from app.database import save_gemini_validation

        save_gemini_validation(sucesso=True, status=200)
    except httpx.HTTPStatusError as e:
        from app.database import save_gemini_validation

        save_gemini_validation(sucesso=False, status=e.response.status_code)
        logger.warning(f"Falha na validação do Gemini: {e}")
        # _listar_modelos já anota falha via registro_fontes.falha() antes de dar raise
    except Exception as e:
        from app.database import save_gemini_validation

        save_gemini_validation(sucesso=False, status=500)
        logger.warning(f"Falha inesperada na validação do Gemini: {e}")


async def laco_da_validacao() -> None:
    # Mesmo controle do monitor do sistema: desliga em teste e com a variável 0
    if "PYTEST_CURRENT_TEST" in os.environ:
        return
    if os.environ.get("MONITOR_SISTEMA", "1") in {"0", "false", "False"}:
        return

    ultima_validacao = 0.0

    while True:
        agora = time.time()
        # Respeita o limite de 1 requisição a cada 2 s por domínio
        if agora - ultima_validacao >= 2.0:
            await validar()
            ultima_validacao = time.time()

        logger.info("Próxima validação do Gemini em %s", INTERVALO)
        await asyncio.sleep(INTERVALO.total_seconds())
