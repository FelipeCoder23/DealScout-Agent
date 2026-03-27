"""Busqueda rapida de productos: solo APIs publicas, sin agentes LLM."""

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.schemas.product import DealResult, ProductListing
from src.tools.mercadolibre import search_mercadolibre
from src.tools.serpapi_shopping import search_google_shopping_chile
from src.tools.solotodo import search_solotodo
from src.utils.price import compare_prices, format_clp


def run_fast_search(query: str, max_budget: int | None = None) -> DealResult:
    """Busqueda rapida: APIs en paralelo + ranking programatico, sin LLM.

    Args:
        query: Nombre del producto
        max_budget: Presupuesto maximo en CLP (opcional)

    Returns:
        DealResult listo para imprimir

    Raises:
        RuntimeError: Si no se encuentran resultados
    """
    start_time = time.time()
    all_raw: list[dict] = []
    sources: list[str] = []

    # ── Paso 1: llamar APIs en paralelo con ThreadPoolExecutor ──────────
    tasks = [
        ("MercadoLibre API", search_mercadolibre, {"query": query, "max_results": 20}),
        ("Solotodo API", search_solotodo, {"query": query, "max_results": 10}),
    ]

    if os.environ.get("SERPAPI_KEY"):
        tasks.append(
            ("Google Shopping (SerpAPI)", search_google_shopping_chile, {"query": query, "max_results": 10})
        )

    if max_budget:
        tasks[0] = (
            "MercadoLibre API",
            search_mercadolibre,
            {"query": query, "max_results": 20, "price_max": max_budget},
        )

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {}
        for source_name, tool_fn, kwargs in tasks:
            future = pool.submit(tool_fn.invoke, kwargs)
            futures[future] = source_name

        for future in as_completed(futures):
            source_name = futures[future]
            try:
                result = future.result(timeout=20)
                if isinstance(result, list) and result:
                    all_raw.extend(result)
                    sources.append(source_name)
            except Exception:
                continue

    # ── Paso 2: convertir dicts a ProductListing, filtrar invalidos ─────
    listings: list[ProductListing] = []
    for raw in all_raw:
        try:
            listing = ProductListing(**raw)
            if max_budget and listing.price > max_budget:
                continue
            listings.append(listing)
        except (ValueError, TypeError):
            continue

    if not listings:
        raise RuntimeError(
            "No se encontraron resultados para la busqueda. "
            "Intenta con otro nombre de producto o usa el modo completo (sin --fast)."
        )

    # ── Paso 3: deduplicar y ordenar por precio ────────────────────────
    ranked = compare_prices(listings)

    # ── Paso 4: seleccionar best deal + alternativas ────────────────────
    best = ranked[0]
    alternatives = ranked[1:10]

    if not alternatives:
        alternatives = [best]

    # ── Paso 5: generar recomendacion programatica ──────────────────────
    recommendation = _build_recommendation(best, alternatives)

    # ── Paso 6: construir y retornar DealResult ─────────────────────────
    duration = time.time() - start_time

    return DealResult(
        query=query,
        best_deal=best,
        alternatives=alternatives,
        price_history=None,
        recommendation=recommendation,
        total_results_found=len(all_raw),
        sources_consulted=sources or ["Ninguna fuente respondio"],
        search_duration_seconds=round(duration, 2),
    )


def _build_recommendation(best: ProductListing, alternatives: list[ProductListing]) -> str:
    """Genera una recomendacion en texto basada en los datos disponibles.

    No usa LLM — construye el texto programaticamente comparando precios,
    tiendas, envio y descuento.

    Args:
        best: El producto con mejor ranking
        alternatives: Lista de alternativas

    Returns:
        Texto de recomendacion en español (2-3 oraciones)
    """
    parts: list[str] = []

    parts.append(
        f"El mejor precio encontrado es {format_clp(best.price)} en {best.store}."
    )

    if alternatives and alternatives[0].price > best.price:
        diff = alternatives[0].price - best.price
        parts.append(
            f"Son {format_clp(diff)} menos que la siguiente opcion "
            f"en {alternatives[0].store} ({format_clp(alternatives[0].price)})."
        )

    extras: list[str] = []

    if best.shipping_info and "gratis" in best.shipping_info.lower():
        extras.append("incluye envio gratis")

    if best.original_price and best.original_price > best.price:
        discount_pct = round((1 - best.price / best.original_price) * 100, 1)
        extras.append(f"tiene {discount_pct}% de descuento")

    if best.rating and best.rating >= 4.0:
        extras.append(f"rating de {best.rating:.1f}/5.0")

    if extras:
        extras_str = ", ".join(extras)
        parts.append(f"Ademas {extras_str}.")

    return " ".join(parts)
