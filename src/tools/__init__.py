"""Tools del agente DealScout para busqueda y extraccion de productos."""

from src.tools.firecrawl_extract import extract_product_from_url, search_and_extract_from_site
from src.tools.knasta import get_price_history
from src.tools.mercadolibre import search_mercadolibre
from src.tools.playwright_scraper import scrape_with_browser
from src.tools.serpapi_shopping import search_google_shopping_chile
from src.tools.solotodo import search_solotodo

# Tools de busqueda en APIs directas (sin scraping, gratis)
SEARCH_TOOLS = [
    search_solotodo,
    search_mercadolibre,
    search_google_shopping_chile,
]

# Tools de extraccion desde paginas web (requieren API keys de pago o Playwright)
EXTRACTION_TOOLS = [
    extract_product_from_url,
    search_and_extract_from_site,
    scrape_with_browser,
]

# Tools de historial de precios
HISTORY_TOOLS = [
    get_price_history,
]

# Todas las tools disponibles
ALL_TOOLS = SEARCH_TOOLS + EXTRACTION_TOOLS + HISTORY_TOOLS

__all__ = [
    "search_solotodo",
    "search_mercadolibre",
    "search_google_shopping_chile",
    "extract_product_from_url",
    "search_and_extract_from_site",
    "scrape_with_browser",
    "get_price_history",
    "SEARCH_TOOLS",
    "EXTRACTION_TOOLS",
    "HISTORY_TOOLS",
    "ALL_TOOLS",
]
