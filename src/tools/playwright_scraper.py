"""Tool de scraping con Playwright como fallback para sitios con JS pesado.

Usar SOLO cuando Firecrawl falla (403, bloqueo, timeout).
Es mas lento y consume mas recursos (una instancia Chromium ~200MB RAM).
"""

from langchain.tools import tool


@tool
def scrape_with_browser(url: str, extract_selector: str | None = None) -> str:
    """Navega a una URL con un navegador Chromium completo y extrae el contenido.

    Usar SOLO como fallback cuando Firecrawl no puede acceder a un sitio (error 403,
    contenido bloqueado, JavaScript muy complejo). Este tool es mas lento y consume
    mas recursos que Firecrawl.

    Args:
        url: URL a navegar (ej: 'https://falabella.com/producto/123')
        extract_selector: CSS selector para extraer contenido especifico (opcional).
            Si no se proporciona, retorna el texto completo de la pagina.

    Returns:
        Contenido de la pagina como texto plano (puede ser HTML parcial o texto limpio).
        Retorna string vacio si falla.
    """
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
                locale="es-CL",
            )
            page = context.new_page()

            try:
                page.goto(url, wait_until="networkidle", timeout=30_000)

                if extract_selector:
                    elements = page.query_selector_all(extract_selector)
                    content = "\n".join(el.inner_text() for el in elements if el)
                else:
                    content = page.inner_text("body")

                return content.strip()

            finally:
                browser.close()

    except ImportError:
        return ""
    except Exception:
        return ""
