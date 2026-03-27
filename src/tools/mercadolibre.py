"""Tool para buscar productos en la API publica de MercadoLibre Chile (MLC).

MercadoLibre es el marketplace mas grande de Chile. Su API no requiere OAuth
para busquedas basicas de productos.
Documentacion: https://developers.mercadolibre.cl/
"""

import httpx
from langchain.tools import tool

from src.schemas.product import ProductListing

_ML_API_BASE = "https://api.mercadolibre.com"
_SITE_ID = "MLC"  # Chile


@tool
def search_mercadolibre(
    query: str,
    max_results: int = 10,
    price_min: int | None = None,
    price_max: int | None = None,
) -> list[dict]:
    """Busca productos en MercadoLibre Chile.

    Cubre practicamente cualquier categoria: electronica, hogar, ropa, deportes,
    videojuegos, etc. Es el marketplace mas grande de Chile con millones de productos
    de vendedores nacionales e internacionales.

    Args:
        query: Nombre del producto (ej: 'PS5', 'iPhone 15 128gb', 'zapatillas running')
        max_results: Maximo de resultados (default: 10, maximo recomendado: 50)
        price_min: Precio minimo en CLP para filtrar (opcional)
        price_max: Precio maximo en CLP para filtrar (opcional)

    Returns:
        Lista de productos con precio, vendedor, envio y link directo.
    """
    results: list[dict] = []

    try:
        params: dict = {
            "q": query,
            "limit": min(max_results, 50),
            "condition": "new",
            "site_id": _SITE_ID,
        }

        if price_min is not None and price_max is not None:
            params["price"] = f"{price_min}-{price_max}"
        elif price_min is not None:
            params["price"] = f"{price_min}-*"
        elif price_max is not None:
            params["price"] = f"*-{price_max}"

        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                f"{_ML_API_BASE}/sites/{_SITE_ID}/search",
                params=params,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()

            items = data.get("results", [])
            for item in items:
                try:
                    price_raw = item.get("price")
                    if not price_raw:
                        continue

                    price = int(float(price_raw))
                    if price <= 0:
                        continue

                    permalink = item.get("permalink", "")
                    if not permalink or not permalink.startswith("http"):
                        continue

                    # Informacion de envio
                    shipping = item.get("shipping", {})
                    free_shipping = shipping.get("free_shipping", False)
                    shipping_info = "Envio gratis" if free_shipping else None

                    # Vendedor
                    seller = item.get("seller", {})
                    seller_nickname = seller.get("nickname", "MercadoLibre")

                    # Rating (seller reputation, no disponible en busqueda basica)
                    rating: float | None = None

                    listing = ProductListing(
                        name=item.get("title", query),
                        price=price,
                        store=f"MercadoLibre ({seller_nickname})",
                        url=permalink,
                        shipping_info=shipping_info,
                        rating=rating,
                        review_count=None,
                        image_url=item.get("thumbnail"),
                        source="mercadolibre_api",
                    )
                    results.append(listing.model_dump())

                except (ValueError, KeyError, TypeError):
                    continue

        return results

    except httpx.TimeoutException:
        return []
    except httpx.HTTPStatusError:
        return []
    except Exception:
        return []
