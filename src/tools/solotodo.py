"""Tool para buscar productos en la API publica de Solotodo.cl.

Solotodo es el principal comparador de tecnologia en Chile con API publica gratuita.
Documentacion: https://publicapi.solotodo.com/
"""


import httpx
from langchain.tools import tool

from src.schemas.product import ProductListing


@tool
def search_solotodo(query: str, max_results: int = 10) -> list[dict]:
    """Busca productos de tecnologia y electronica en Solotodo.cl.

    Ideal para laptops, celulares, GPUs, monitores, componentes de PC, y electrodomesticos.
    Retorna precios actuales de multiples tiendas chilenas con links directos.
    NO usar para ropa, comida, o productos no tecnologicos.

    Args:
        query: Nombre del producto a buscar (ej: 'iPhone 15', 'notebook gamer', 'GPU RTX 4070')
        max_results: Maximo de resultados a retornar (default: 10)

    Returns:
        Lista de productos encontrados con precio, tienda y link directo.
    """
    base_url = "https://publicapi.solotodo.com"
    results: list[dict] = []

    try:
        with httpx.Client(timeout=15.0) as client:
            # Buscar productos
            response = client.get(
                f"{base_url}/products/",
                params={"search": query, "page_size": max_results},
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()

            products = data.get("results", [])
            if not products:
                return []

            # Para cada producto, buscar sus entities (una por tienda)
            for product in products:
                product_id = product.get("id")
                product_name = product.get("name", "")

                if not product_id:
                    continue

                # Obtener entidades (listings por tienda) del producto
                entities_resp = client.get(
                    f"{base_url}/entities/",
                    params={
                        "product": product_id,
                        "page_size": 20,
                        "ordering": "active_registry__offer_price",
                    },
                    headers={"Accept": "application/json"},
                )

                if entities_resp.status_code != 200:
                    continue

                entities_data = entities_resp.json()
                entities = entities_data.get("results", [])

                for entity in entities:
                    try:
                        registry = entity.get("active_registry", {})
                        offer_price = registry.get("offer_price")
                        normal_price = registry.get("normal_price")
                        cell_plan_price = registry.get("cell_plan_price")

                        # Usar precio de oferta si existe, sino precio normal
                        price_raw = offer_price or normal_price or cell_plan_price
                        if not price_raw:
                            continue

                        price = int(float(price_raw))
                        if price <= 0:
                            continue

                        store_info = entity.get("store", {})
                        store_name = store_info.get("name", "Desconocida")

                        external_url = entity.get("external_url", "")
                        if not external_url or not external_url.startswith("http"):
                            continue

                        original_price = None
                        if normal_price and offer_price and int(float(normal_price)) > price:
                            original_price = int(float(normal_price))

                        listing = ProductListing(
                            name=product_name,
                            price=price,
                            store=store_name,
                            url=external_url,
                            original_price=original_price,
                            source="solotodo_api",
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
