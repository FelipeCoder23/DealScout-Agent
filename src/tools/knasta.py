"""Tool para obtener historial de precios desde Knasta.cl.

Knasta es el principal rastreador de precios de Chile.
Muestra historial de precios de multiples tiendas.
No tiene API publica, se scrape server-side.
"""

from langchain.tools import tool

from src.schemas.product import PriceHistory, PricePoint


@tool
def get_price_history(
    product_name: str,
    product_url: str | None = None,
) -> dict | None:
    """Consulta el historial de precios de un producto en Knasta.cl.

    Knasta es el principal rastreador de precios de Chile, similar a CamelCamelCamel.
    Retorna precios historicos para validar si el precio actual es realmente bueno.
    Usar DESPUES de haber encontrado el producto en otras fuentes.

    Args:
        product_name: Nombre del producto para buscar en Knasta
        product_url: URL del producto en alguna tienda (ayuda a encontrar el match exacto)

    Returns:
        Diccionario con historial de precios, o None si no se encuentra el producto.
    """
    try:
        from datetime import date

        import httpx
        from bs4 import BeautifulSoup

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "es-CL,es;q=0.9",
        }

        with httpx.Client(timeout=15.0, headers=headers, follow_redirects=True) as client:
            # Buscar el producto en Knasta
            search_resp = client.get(
                "https://knasta.cl/search",
                params={"q": product_name},
            )

            if search_resp.status_code != 200:
                return None

            soup = BeautifulSoup(search_resp.text, "html.parser")

            # Buscar primer resultado relevante
            # Knasta usa diferentes estructuras segun la categoria
            product_links = soup.select("a[href*='/producto/'], a[href*='/p/']")
            if not product_links:
                return None

            first_link = product_links[0]
            product_href = first_link.get("href", "")
            if not product_href:
                return None

            product_page_url = (
                product_href if product_href.startswith("http")
                else f"https://knasta.cl{product_href}"
            )

            # Obtener pagina del producto con historial
            product_resp = client.get(product_page_url)
            if product_resp.status_code != 200:
                return None

            product_soup = BeautifulSoup(product_resp.text, "html.parser")

            # Extraer datos de historial de precios
            # Knasta muestra precios en elementos con clases especificas
            price_elements = product_soup.select("[data-price], .price-history-item, .price-point")

            if not price_elements:
                # Intentar extraer precio actual al menos
                current_price_el = product_soup.select_one(".price, .current-price, [class*='price']")
                if not current_price_el:
                    return None

                # Crear historial minimo con precio actual
                price_text = current_price_el.get_text(strip=True)
                price = _parse_clp_price(price_text)
                if not price:
                    return None

                today = date.today()
                history = PriceHistory(
                    product_name=product_name,
                    store="Knasta (multiples tiendas)",
                    prices=[PricePoint(price=price, recorded_at=today)],
                    average_price=price,
                    lowest_price=price,
                    highest_price=price,
                )
                return history.model_dump()

            # Parsear multiples puntos de precio
            price_points: list[PricePoint] = []
            for el in price_elements:
                price_str = el.get("data-price") or el.get_text(strip=True)
                price = _parse_clp_price(price_str)
                if price and price > 0:
                    price_points.append(PricePoint(price=price, recorded_at=date.today()))

            if not price_points:
                return None

            prices = [p.price for p in price_points]
            history = PriceHistory(
                product_name=product_name,
                store="Knasta (multiples tiendas)",
                prices=price_points,
                average_price=int(sum(prices) / len(prices)),
                lowest_price=min(prices),
                highest_price=max(prices),
            )
            return history.model_dump()

    except ImportError:
        return None
    except Exception:
        return None


def _parse_clp_price(price_str: str) -> int | None:
    """Parsea un string de precio chileno a entero CLP."""
    if not price_str:
        return None
    # Remover simbolos y texto, mantener solo digitos y punto como separador de miles
    clean = ""
    for char in price_str:
        if char.isdigit():
            clean += char
    if not clean:
        return None
    try:
        return int(clean)
    except ValueError:
        return None
