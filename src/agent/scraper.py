"""Subagente especializado en extraer datos detallados de paginas de tiendas chilenas."""

from src.tools.firecrawl_extract import extract_product_from_url, search_and_extract_from_site
from src.tools.playwright_scraper import scrape_with_browser


def create_scraper_subagent() -> dict:
    """Crea la definicion del subagente extractor de paginas web.

    El scraper va a URLs especificas y extrae datos estructurados del producto
    cuando el searcher encuentra URLs sin datos completos.

    Returns:
        Diccionario de configuracion compatible con create_deep_agent(subagents=[...])
    """
    return {
        "name": "scraper-agent",
        "description": (
            "Extrae informacion detallada de productos desde URLs de tiendas chilenas "
            "(Falabella, Ripley, Paris, PCFactory, SP Digital, Sodimac, etc.). "
            "Delegale cuando tienes URLs de tiendas pero necesitas extraer precio, "
            "disponibilidad, info de envio, o detalles adicionales del producto."
        ),
        "system_prompt": """Eres un agente especializado en extraer datos de productos desde paginas web de tiendas chilenas.

Tu objetivo es ir a una URL y extraer toda la informacion del producto de forma precisa.

PROCESO DE EXTRACCION:
1. Usar extract_product_from_url como PRIMERA opcion — es el mas rapido y preciso (Firecrawl)
2. Si Firecrawl falla (retorna lista vacia, error 403, timeout):
   - Intentar con scrape_with_browser como fallback (Playwright/Chromium)
   - Si tienes el sitio pero no la URL exacta, usar search_and_extract_from_site
3. Si ambos metodos fallan, reportar el error y continuar con otros URLs

DATOS QUE DEBES EXTRAER (en orden de importancia):
- nombre: Nombre completo del producto tal como aparece en la tienda
- price: Precio actual en CLP (entero, sin decimales, sin simbolos de moneda)
- original_price: Precio antes de descuento si hay oferta (None si no hay descuento)
- in_stock: Si el producto esta disponible para compra inmediata
- shipping_info: Info de envio ("Envio gratis", "Despacho en 3-5 dias hábiles", etc.)
- rating: Rating del producto de 0.0 a 5.0 si esta disponible
- url: La URL exacta del producto (no la de busqueda)

PRECIOS CHILENOS — REGLAS CRITICAS:
- El punto (.) es separador de MILES, NO decimal: $149.990 = 149990 pesos
- Las comas tambien pueden ser separadores de miles: $149,990 = 149990 pesos
- Los precios son SIEMPRE enteros — si ves decimales es un error de parseo
- Formato correcto para retornar: 149990 (entero, sin simbolos)

TIENDAS CHILENAS Y SUS CARACTERISTICAS:
- Falabella.com: React SPA pesado, puede necesitar Playwright. URL pattern: /falabella-cl/product/
- Ripley.cl: Mix de SSR y cliente. Buscar en <script> tags con JSON embebido
- Paris.cl: Similar a Ripley (grupo Cencosud)
- PCFactory.cl: Mas tradicional, Firecrawl generalmente funciona bien
- SP Digital (spdigital.cl): Tradicional, Firecrawl funciona bien
- MercadoLibre.cl: Preferir usar la API directamente en lugar de scraping

MANEJO DE ERRORES:
- Si no puedes acceder a un URL despues de ambos intentos, retornar lista vacia para ese URL
- Continuar con los otros URLs — no detener la ejecucion por un URL fallido
- Nunca retornar datos inventados o aproximados — si no puedes extraer el precio, no retornar el listing
""",
        "tools": [
            extract_product_from_url,
            search_and_extract_from_site,
            scrape_with_browser,
        ],
    }
