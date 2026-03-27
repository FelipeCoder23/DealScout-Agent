"""Tools para extraer datos estructurados de paginas web usando Firecrawl.

Firecrawl maneja JavaScript rendering, anti-bot y retorna datos estructurados.
94% de accuracy en extraccion de e-commerce. Desde $16/mes.
Documentacion: https://docs.firecrawl.dev/
"""

import os

from langchain.tools import tool

from src.schemas.product import ProductListing

# Schema JSON para extraccion estructurada de productos
_PRODUCT_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Nombre completo del producto"},
        "price": {"type": "number", "description": "Precio actual en CLP (solo numero, sin simbolos)"},
        "original_price": {
            "type": "number",
            "description": "Precio original antes de descuento en CLP (solo si hay oferta)",
        },
        "in_stock": {"type": "boolean", "description": "Si el producto esta disponible para compra"},
        "shipping_info": {
            "type": "string",
            "description": "Informacion de envio (ej: 'Envio gratis', 'Despacho 3-5 dias')",
        },
        "rating": {"type": "number", "description": "Rating del producto de 0 a 5"},
        "review_count": {"type": "integer", "description": "Cantidad de reviews"},
        "image_url": {"type": "string", "description": "URL de la imagen principal del producto"},
    },
    "required": ["name", "price"],
}


@tool
def extract_product_from_url(url: str, store_name: str = "Unknown") -> list[dict]:
    """Extrae informacion estructurada de un producto desde una URL de tienda chilena.

    Usa Firecrawl para renderizar JavaScript y extraer datos de forma precisa.
    Ideal para URLs de Falabella, Ripley, Paris, PCFactory, SP Digital, y cualquier
    tienda con paginas de producto. Pasarle la URL directa del producto.

    Args:
        url: URL directa de la pagina del producto (ej: 'https://falabella.com/producto/123')
        store_name: Nombre de la tienda para el registro (ej: 'Falabella', 'Ripley')

    Returns:
        Lista con un ProductListing si la extraccion fue exitosa, lista vacia si falla.
    """
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        return []

    try:
        from firecrawl import FirecrawlApp

        app = FirecrawlApp(api_key=api_key)

        result = app.scrape_url(
            url,
            formats=["extract"],
            extract={"schema": _PRODUCT_EXTRACTION_SCHEMA},
        )

        if not result or not result.extract:
            return []

        extracted = result.extract
        price_raw = extracted.get("price")
        if not price_raw:
            return []

        price = int(float(price_raw))
        if price <= 0:
            return []

        # Precio original (solo si existe y es mayor al actual)
        original_price: int | None = None
        original_raw = extracted.get("original_price")
        if original_raw:
            original_candidate = int(float(original_raw))
            if original_candidate > price:
                original_price = original_candidate

        listing = ProductListing(
            name=extracted.get("name", f"Producto en {store_name}"),
            price=price,
            store=store_name,
            url=url,
            in_stock=extracted.get("in_stock", True),
            original_price=original_price,
            shipping_info=extracted.get("shipping_info"),
            rating=extracted.get("rating"),
            review_count=extracted.get("review_count"),
            image_url=extracted.get("image_url"),
            source="firecrawl",
        )
        return [listing.model_dump()]

    except ImportError:
        return []
    except Exception:
        return []


@tool
def search_and_extract_from_site(
    query: str,
    site_url: str,
    max_results: int = 5,
) -> list[dict]:
    """Busca un producto en un sitio web especifico y extrae resultados estructurados.

    Util para buscar directamente en Falabella.com, Ripley.cl, Paris.cl, PCFactory.cl, etc.
    Combina busqueda web + extraccion estructurada de Firecrawl.

    Args:
        query: Nombre del producto a buscar
        site_url: Dominio del sitio donde buscar (ej: 'falabella.com', 'ripley.cl')
        max_results: Maximo de resultados a extraer (default: 5)

    Returns:
        Lista de ProductListing encontrados en ese sitio.
    """
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        return []

    results: list[dict] = []

    try:
        from firecrawl import FirecrawlApp

        app = FirecrawlApp(api_key=api_key)

        # Buscar usando Firecrawl search con filtro de sitio
        search_results = app.search(
            query=f"{query} site:{site_url}",
            limit=max_results,
        )

        if not search_results:
            return []

        # Determinar nombre de la tienda desde el dominio
        store_name = _domain_to_store_name(site_url)

        # Extraer datos de cada URL encontrada
        for result in search_results[:max_results]:
            url = result.get("url", "")
            if not url or not url.startswith("http"):
                continue

            extracted = extract_product_from_url.invoke({"url": url, "store_name": store_name})
            if extracted:
                results.extend(extracted if isinstance(extracted, list) else [extracted])

        return results

    except ImportError:
        return []
    except Exception:
        return []


def _domain_to_store_name(domain: str) -> str:
    """Convierte un dominio a nombre de tienda legible."""
    mapping = {
        "falabella.com": "Falabella",
        "ripley.cl": "Ripley",
        "paris.cl": "Paris",
        "pcfactory.cl": "PCFactory",
        "spdigital.cl": "SP Digital",
        "sodimac.cl": "Sodimac",
        "hites.com": "Hites",
        "abcdin.cl": "ABCDIN",
        "corona.cl": "Corona",
        "lider.cl": "Lider",
        "jumbo.cl": "Jumbo",
        "microplay.cl": "Microplay",
    }
    for key, name in mapping.items():
        if key in domain:
            return name
    # Capitalizar el dominio como fallback
    return domain.replace(".cl", "").replace(".com", "").capitalize()
