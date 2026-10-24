import logging
from app.consultor.calculador import calcular_consultor
from app.consultor.armazenamento import save_recomendacoes, save_fechamentos

logger = logging.getLogger(__name__)


def collect_and_save() -> bool:
    try:
        dados = calcular_consultor(ignorar_cache=True)

        if "resultados" not in dados:
            return False

        flat_resultados = []
        for group_name, items in dados["resultados"].items():
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
        return True
    except Exception as e:
        logger.error(f"Erro no coletor consultor_fechamento: {e}", exc_info=True)
        return False
