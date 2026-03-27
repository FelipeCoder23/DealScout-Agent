# Plan: Modo --fast (búsqueda rápida sin agentes)

## Problema

El modo completo (agentes con DeepAgent) tarda ~30-50 minutos porque:
1. Orquesta 4+ llamadas LLM secuenciales (master → searcher → scraper → comparator)
2. El scraper intenta Firecrawl + Playwright en tiendas individuales (lentos, frágiles)
3. Cada subagente tiene ida y vuelta completa con Claude

## Solución

Crear un modo `--fast` / `-f` que:
- Llama las APIs públicas (MercadoLibre + Solotodo + SerpAPI) **en paralelo** usando threads
- Rankea y recomienda **programáticamente** (sin ninguna llamada LLM)
- Retorna el mismo `DealResult` que el modo completo
- **Objetivo: 10-15 segundos total**

## Archivos a crear/modificar

### 1. CREAR `src/fast_search.py` (archivo nuevo — core de la feature)

```python
"""Busqueda rapida de productos: solo APIs publicas, sin agentes LLM."""

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.schemas.product import DealResult, ProductListing
from src.tools.mercadolibre import search_mercadolibre
from src.tools.solotodo import search_solotodo
from src.tools.serpapi_shopping import search_google_shopping_chile
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
    # Definir tareas como tuplas (nombre_fuente, callable, kwargs)
    tasks = [
        ("MercadoLibre API", search_mercadolibre, {"query": query, "max_results": 20}),
        ("Solotodo API", search_solotodo, {"query": query, "max_results": 10}),
    ]

    # Solo agregar SerpAPI si la key existe
    if os.environ.get("SERPAPI_KEY"):
        tasks.append(
            ("Google Shopping (SerpAPI)", search_google_shopping_chile, {"query": query, "max_results": 10})
        )

    # Si hay presupuesto, agregar filtro de precio a MercadoLibre
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
                # Las tools retornan list[dict] o un dict (SerpAPI sin key)
                if isinstance(result, list) and result:
                    all_raw.extend(result)
                    sources.append(source_name)
            except Exception:
                # Si una API falla, continuar con las otras
                continue

    # ── Paso 2: convertir dicts a ProductListing, filtrar invalidos ─────
    listings: list[ProductListing] = []
    for raw in all_raw:
        try:
            listing = ProductListing(**raw)
            # Aplicar filtro de presupuesto
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
    alternatives = ranked[1:10]  # hasta 9 alternativas

    # Necesitamos al menos 1 alternativa para DealResult
    # Si solo hay 1 resultado, duplicar como alternativa con nota
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
        price_history=None,  # modo rapido no consulta historial
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

    # Oracion 1: mejor precio + tienda
    parts.append(
        f"El mejor precio encontrado es {format_clp(best.price)} en {best.store}."
    )

    # Oracion 2: comparar con siguiente alternativa
    if alternatives and alternatives[0].price > best.price:
        diff = alternatives[0].price - best.price
        parts.append(
            f"Son {format_clp(diff)} menos que la siguiente opcion "
            f"en {alternatives[0].store} ({format_clp(alternatives[0].price)})."
        )

    # Oracion 3: info extra (envio, descuento)
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
        # Capitalizar primera letra
        parts.append(f"Ademas {extras_str}.")

    return " ".join(parts)
```

#### Decisiones clave de `fast_search.py`:

- **`ThreadPoolExecutor(max_workers=3)`**: llama MercadoLibre, Solotodo y SerpAPI al mismo tiempo. Como son llamadas HTTP (I/O), threads son suficientes (no necesita async).
- **`future.result(timeout=20)`**: si una API no responde en 20 segundos, la ignora y sigue con las otras.
- **Usa `tool_fn.invoke(kwargs)`**: las tools de LangChain se invocan con `.invoke()` que acepta un dict de argumentos.
- **`compare_prices(listings)`** ya existe en `src/utils/price.py` — deduplica por (store, price_bucket±1000) y ordena por precio ascendente.
- **`_build_recommendation()`**: genera texto sin LLM. Es menos inteligente que el modo completo pero es instantáneo.
- **Si solo hay 1 resultado**: lo duplica como alternativa (DealResult requiere min_length=1 en alternatives).

---

### 2. MODIFICAR `cli.py` — agregar flag `--fast / -f`

**Ubicación del cambio**: en la función `search()`, agregar parámetro:

```python
# AGREGAR este parametro despues de verbose:
fast: bool = typer.Option(
    False,
    "--fast",
    "-f",
    help="Busqueda rapida: solo APIs publicas, sin scraping ni agentes (~15s)",
),
```

**Pasar a `main()`**: cambiar la llamada dentro del `console.status(...)`:

```python
# Cambiar el mensaje del spinner segun modo
spinner_msg = (
    "[bold green]Busqueda rapida en MercadoLibre, Solotodo...[/bold green]"
    if fast
    else "[bold green]Buscando en Solotodo, MercadoLibre, Google Shopping Chile...[/bold green]"
)

with console.status(spinner_msg, spinner="dots"):
    result = main(query=product, budget=budget, fast=fast)
```

**En el header**, mostrar el modo activo:

```python
# Despues de la linea que imprime "DealScout — Buscando en el mercado chileno"
if fast:
    console.print("[yellow]Modo rapido[/yellow] [dim](solo APIs publicas, sin agentes)[/dim]")
```

---

### 3. MODIFICAR `src/main.py` — aceptar flag `fast` y rutear

```python
def main(query: str, budget: int | None = None, fast: bool = False) -> DealResult:
    """Ejecuta una busqueda de producto en el mercado chileno.

    Args:
        query: Nombre del producto a buscar
        budget: Presupuesto maximo en CLP (opcional)
        fast: Si True, usar busqueda rapida sin agentes

    Returns:
        DealResult con la mejor opcion y alternativas
    """
    load_dotenv()

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    logging.getLogger("langgraph").setLevel(logging.WARNING)

    if fast:
        from src.fast_search import run_fast_search
        return run_fast_search(query=query, max_budget=budget)

    return run_search(query=query, max_budget=budget)
```

**Nota importante**: en modo `--fast` NO se valida `ANTHROPIC_API_KEY` porque no se usa LLM. Mover la validación de API key en `cli.py` para que solo aplique cuando `fast=False`:

```python
# En cli.py, cambiar la validacion de ANTHROPIC_API_KEY:
if not fast and not os.environ.get("ANTHROPIC_API_KEY"):
    print_error(
        "ANTHROPIC_API_KEY no configurada.\n\n"
        "1. Copia el archivo de ejemplo: cp .env.example .env\n"
        "2. Edita .env y agrega tu API key de Anthropic\n"
        "   Obtener en: https://console.anthropic.com/\n\n"
        "Tip: usa --fast para buscar sin API key (solo APIs publicas)"
    )
    raise typer.Exit(code=1)
```

---

### 4. CREAR `tests/unit/test_fast_search.py` (tests unitarios)

```python
"""Tests unitarios para el modo de busqueda rapida."""

import pytest
from unittest.mock import patch

from src.fast_search import run_fast_search, _build_recommendation
from src.schemas.product import ProductListing, DealResult
from src.utils.price import format_clp


# ─── Helpers ──────────────────────────────────────────────────────────────

def _make_listing(**overrides) -> ProductListing:
    """Crea un ProductListing de prueba con valores por defecto."""
    defaults = {
        "name": "PlayStation 5",
        "price": 599990,
        "store": "MercadoLibre (Tienda Oficial)",
        "url": "https://www.mercadolibre.cl/ps5/p/MLC12345",
        "source": "mercadolibre_api",
    }
    defaults.update(overrides)
    return ProductListing(**defaults)


# ─── Tests de _build_recommendation ──────────────────────────────────────

class TestBuildRecommendation:

    def test_basic_recommendation(self):
        best = _make_listing(price=599990, store="MercadoLibre")
        alts = [_make_listing(price=649990, store="Falabella", url="https://falabella.com/p/1")]
        rec = _build_recommendation(best, alts)
        assert "$599.990" in rec
        assert "MercadoLibre" in rec

    def test_includes_savings_vs_alternative(self):
        best = _make_listing(price=500000, store="PCFactory")
        alts = [_make_listing(price=600000, store="Ripley", url="https://ripley.cl/p/1")]
        rec = _build_recommendation(best, alts)
        assert "$100.000" in rec  # diferencia
        assert "Ripley" in rec

    def test_includes_free_shipping(self):
        best = _make_listing(price=500000, shipping_info="Envio gratis")
        alts = [_make_listing(price=600000, url="https://other.cl/p/1")]
        rec = _build_recommendation(best, alts)
        assert "envio gratis" in rec.lower()

    def test_includes_discount(self):
        best = _make_listing(price=500000, original_price=700000)
        alts = [_make_listing(price=600000, url="https://other.cl/p/1")]
        rec = _build_recommendation(best, alts)
        assert "descuento" in rec.lower()

    def test_includes_rating(self):
        best = _make_listing(price=500000, rating=4.8)
        alts = [_make_listing(price=600000, url="https://other.cl/p/1")]
        rec = _build_recommendation(best, alts)
        assert "4.8" in rec

    def test_no_extras_when_none(self):
        """Sin envio, descuento ni rating, no debe haber oracion 'Ademas...'"""
        best = _make_listing(price=500000)
        alts = [_make_listing(price=500000)]  # misma como alt
        rec = _build_recommendation(best, alts)
        assert "Ademas" not in rec

    def test_same_price_no_savings_line(self):
        """Si la alternativa tiene el mismo precio, no mencionar ahorro."""
        best = _make_listing(price=500000, store="Store A")
        alts = [_make_listing(price=500000, store="Store B")]
        rec = _build_recommendation(best, alts)
        assert "menos" not in rec


# ─── Tests de run_fast_search (con APIs mockeadas) ────────────────────────

class TestRunFastSearch:

    def _mock_ml_results(self):
        """Simula respuesta de MercadoLibre."""
        return [
            _make_listing(price=599990, store="ML Vendedor 1", url="https://mercadolibre.cl/1").model_dump(),
            _make_listing(price=649990, store="ML Vendedor 2", url="https://mercadolibre.cl/2").model_dump(),
        ]

    def _mock_solotodo_results(self):
        """Simula respuesta de Solotodo."""
        return [
            _make_listing(price=619990, store="PCFactory", url="https://pcfactory.cl/1", source="solotodo_api").model_dump(),
        ]

    @patch("src.fast_search.search_google_shopping_chile")
    @patch("src.fast_search.search_solotodo")
    @patch("src.fast_search.search_mercadolibre")
    def test_returns_deal_result(self, mock_ml, mock_st, mock_gs, monkeypatch):
        monkeypatch.delenv("SERPAPI_KEY", raising=False)
        mock_ml.invoke.return_value = self._mock_ml_results()
        mock_st.invoke.return_value = self._mock_solotodo_results()
        result = run_fast_search("PS5")
        assert isinstance(result, DealResult)
        assert result.best_deal.price == 599990  # el mas barato

    @patch("src.fast_search.search_google_shopping_chile")
    @patch("src.fast_search.search_solotodo")
    @patch("src.fast_search.search_mercadolibre")
    def test_alternatives_sorted_by_price(self, mock_ml, mock_st, mock_gs, monkeypatch):
        monkeypatch.delenv("SERPAPI_KEY", raising=False)
        mock_ml.invoke.return_value = self._mock_ml_results()
        mock_st.invoke.return_value = self._mock_solotodo_results()
        result = run_fast_search("PS5")
        alt_prices = [a.price for a in result.alternatives]
        assert alt_prices == sorted(alt_prices)

    @patch("src.fast_search.search_google_shopping_chile")
    @patch("src.fast_search.search_solotodo")
    @patch("src.fast_search.search_mercadolibre")
    def test_respects_budget_filter(self, mock_ml, mock_st, mock_gs, monkeypatch):
        monkeypatch.delenv("SERPAPI_KEY", raising=False)
        mock_ml.invoke.return_value = self._mock_ml_results()
        mock_st.invoke.return_value = self._mock_solotodo_results()
        result = run_fast_search("PS5", max_budget=620000)
        # Solo deberian quedar los que cuestan <= 620000
        assert result.best_deal.price <= 620000
        for alt in result.alternatives:
            assert alt.price <= 620000

    @patch("src.fast_search.search_google_shopping_chile")
    @patch("src.fast_search.search_solotodo")
    @patch("src.fast_search.search_mercadolibre")
    def test_raises_when_no_results(self, mock_ml, mock_st, mock_gs, monkeypatch):
        monkeypatch.delenv("SERPAPI_KEY", raising=False)
        mock_ml.invoke.return_value = []
        mock_st.invoke.return_value = []
        with pytest.raises(RuntimeError, match="No se encontraron"):
            run_fast_search("producto inexistente xyz")

    @patch("src.fast_search.search_google_shopping_chile")
    @patch("src.fast_search.search_solotodo")
    @patch("src.fast_search.search_mercadolibre")
    def test_sources_tracked(self, mock_ml, mock_st, mock_gs, monkeypatch):
        monkeypatch.delenv("SERPAPI_KEY", raising=False)
        mock_ml.invoke.return_value = self._mock_ml_results()
        mock_st.invoke.return_value = self._mock_solotodo_results()
        result = run_fast_search("PS5")
        assert "MercadoLibre API" in result.sources_consulted
        assert "Solotodo API" in result.sources_consulted

    @patch("src.fast_search.search_google_shopping_chile")
    @patch("src.fast_search.search_solotodo")
    @patch("src.fast_search.search_mercadolibre")
    def test_survives_one_api_failure(self, mock_ml, mock_st, mock_gs, monkeypatch):
        """Si Solotodo falla, debe continuar con MercadoLibre."""
        monkeypatch.delenv("SERPAPI_KEY", raising=False)
        mock_ml.invoke.return_value = self._mock_ml_results()
        mock_st.invoke.side_effect = Exception("connection timeout")
        result = run_fast_search("PS5")
        assert isinstance(result, DealResult)
        assert "MercadoLibre API" in result.sources_consulted
        assert "Solotodo API" not in result.sources_consulted

    @patch("src.fast_search.search_google_shopping_chile")
    @patch("src.fast_search.search_solotodo")
    @patch("src.fast_search.search_mercadolibre")
    def test_duration_is_measured(self, mock_ml, mock_st, mock_gs, monkeypatch):
        monkeypatch.delenv("SERPAPI_KEY", raising=False)
        mock_ml.invoke.return_value = self._mock_ml_results()
        mock_st.invoke.return_value = []
        result = run_fast_search("PS5")
        assert result.search_duration_seconds >= 0
        assert result.search_duration_seconds < 60  # tests son rapidos

    @patch("src.fast_search.search_google_shopping_chile")
    @patch("src.fast_search.search_solotodo")
    @patch("src.fast_search.search_mercadolibre")
    def test_single_result_still_works(self, mock_ml, mock_st, mock_gs, monkeypatch):
        """Con un solo resultado, debe funcionar (alternativa = mismo producto)."""
        monkeypatch.delenv("SERPAPI_KEY", raising=False)
        mock_ml.invoke.return_value = [
            _make_listing(price=599990).model_dump()
        ]
        mock_st.invoke.return_value = []
        result = run_fast_search("PS5")
        assert isinstance(result, DealResult)
        assert len(result.alternatives) >= 1
```

---

### 5. Verificación final

Despues de implementar, correr:

```bash
# Tests unitarios (deben pasar todos, los nuevos + los 95 existentes)
uv run pytest tests/unit/ -v

# Linting
uv run ruff check .

# Smoke test sin API key de Anthropic (modo fast no la necesita)
uv run python cli.py "PS5" --fast

# Smoke test con ayuda
uv run python cli.py --help
# Debe mostrar la nueva opcion --fast / -f en la ayuda
```

---

## Resumen de cambios

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `src/fast_search.py` | **CREAR** | Core: APIs en paralelo + ranking + recomendacion programatica |
| `src/main.py` | **MODIFICAR** | Agregar parametro `fast`, rutear a `run_fast_search` |
| `cli.py` | **MODIFICAR** | Agregar `--fast / -f`, condicionar validacion de ANTHROPIC_API_KEY, spinner distinto |
| `tests/unit/test_fast_search.py` | **CREAR** | 14 tests: recommendation builder + búsqueda con mocks |

## Lo que NO cambia

- `src/agent/` — los subagentes quedan intactos (modo completo sigue igual)
- `src/schemas/product.py` — se reutiliza DealResult y ProductListing sin cambios
- `src/tools/` — se reutilizan las tools existentes, llamadas directamente con `.invoke()`
- `src/utils/price.py` — `compare_prices()` y `format_clp()` se reusan tal cual

## Comparación de modos

| | Modo completo (default) | Modo `--fast` |
|---|---|---|
| Tiempo estimado | 30-50 min | 10-15 seg |
| Requiere ANTHROPIC_API_KEY | Sí | No |
| Fuentes | MercadoLibre + Solotodo + SerpAPI + Firecrawl + Playwright | MercadoLibre + Solotodo + SerpAPI |
| Inteligencia | Alta (Claude analiza y recomienda) | Media (ranking programático) |
| Costo por búsqueda | ~$0.10-0.50 en tokens | $0 (solo APIs gratuitas) |
| Recomendación | Escrita por Claude, contextual | Template programático, factual |
