"""Modulo principal de DealScout — entry point para ejecucion programatica."""

import logging

from dotenv import load_dotenv

from src.agent.master import run_search
from src.schemas.product import DealResult


def main(query: str, budget: int | None = None) -> DealResult:
    """Ejecuta una busqueda de producto en el mercado chileno.

    Carga variables de entorno, configura logging y delega al master agent.

    Args:
        query: Nombre del producto a buscar
        budget: Presupuesto maximo en CLP (opcional)

    Returns:
        DealResult con la mejor opcion y alternativas
    """
    load_dotenv()

    # Configurar logging basico (suprimir logs verbosos de librerías externas)
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    logging.getLogger("langgraph").setLevel(logging.WARNING)

    return run_search(query=query, max_budget=budget)
