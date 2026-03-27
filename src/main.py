"""Modulo principal de DealScout — entry point para ejecucion programatica."""

import logging

from dotenv import load_dotenv

from src.agent.master import run_search
from src.schemas.product import DealResult


def main(query: str, budget: int | None = None, fast: bool = False) -> DealResult:
    """Ejecuta una busqueda de producto en el mercado chileno.

    Carga variables de entorno, configura logging y delega al agente o al modo rapido.

    Args:
        query: Nombre del producto a buscar
        budget: Presupuesto maximo en CLP (opcional)
        fast: Si True, usar busqueda rapida sin agentes LLM

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

    if fast:
        from src.fast_search import run_fast_search
        return run_fast_search(query=query, max_budget=budget)

    return run_search(query=query, max_budget=budget)
