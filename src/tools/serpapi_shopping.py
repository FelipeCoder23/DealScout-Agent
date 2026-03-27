"""Tool para buscar productos en Google Shopping Chile via SerpAPI.

SerpAPI permite acceder a resultados de Google Shopping filtrados por Chile.
Free tier: 250 busquedas/mes.
Documentacion: https://serpapi.com/google-shopping-api
"""

import os

from langchain.tools import tool

from src.schemas.product import ProductListing
from src.schemas.search import SearchResult


@tool
def search_google_shopping_chile(query: str, max_results: int = 10) -> list[dict]:
    """Busca productos en Google Shopping enfocado en Chile.

    Util para descubrir tiendas y precios que no estan en Solotodo o MercadoLibre.
    Cubre amplia variedad de tiendas chilenas (Falabella, Ripley, Paris, PCFactory, etc).
    Usar como complemento a las busquedas en APIs directas para mayor cobertura.

    Args:
        query: Nombre del producto (ej: 'Samsung Galaxy S25', 'aspiradora robot')
        max_results: Maximo de resultados (default: 10)

    Returns:
        Lista de productos con precio, tienda y link a Google Shopping.
    """
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        return SearchResult(
            listings=[],
            source="serpapi",
            raw_query=query,
            success=False,
            error_message="SERPAPI_KEY no configurada. Obtener en https://serpapi.com/ (free tier: 250/mes)",
        ).model_dump()

    results: list[dict] = []

    try:
        from serpapi import GoogleSearch

        params = {
            "engine": "google_shopping",
            "q": query,
            "location": "Chile",
            "gl": "cl",
            "hl": "es",
            "num": str(max_results),
            "api_key": api_key,
        }

        search = GoogleSearch(params)
        data = search.get_dict()

        shopping_results = data.get("shopping_results", [])
        for item in shopping_results[:max_results]:
            try:
                # SerpAPI retorna precios como string con simbolo de moneda
                price_raw = item.get("extracted_price") or item.get("price", "")

                # Convertir a int (Google Shopping Chile ya muestra en CLP)
                if isinstance(price_raw, (int, float)):
                    price = int(price_raw)
                elif isinstance(price_raw, str):
                    # Limpiar "$", ".", "," del string
                    clean = price_raw.replace("$", "").replace(".", "").replace(",", "").strip()
                    if not clean:
                        continue
                    price = int(float(clean))
                else:
                    continue

                if price <= 0:
                    continue

                # URL del producto
                product_url = item.get("product_link") or item.get("link", "")
                if not product_url or not product_url.startswith("http"):
                    continue

                # Tienda
                store = item.get("source", "Google Shopping")

                # Rating y reviews
                rating_raw = item.get("rating")
                rating: float | None = float(rating_raw) if rating_raw else None

                reviews_raw = item.get("reviews")
                review_count: int | None = int(reviews_raw) if reviews_raw else None

                listing = ProductListing(
                    name=item.get("title", query),
                    price=price,
                    store=store,
                    url=product_url,
                    rating=rating,
                    review_count=review_count,
                    image_url=item.get("thumbnail"),
                    source="serpapi",
                )
                results.append(listing.model_dump())

            except (ValueError, KeyError, TypeError):
                continue

        return results

    except ImportError:
        return []
    except Exception:
        return []
