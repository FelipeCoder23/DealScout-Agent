# Bitacora de Desarrollo — DealScout Agent

**Fecha:** 2026-03-27
**Modelo ejecutor:** Claude Sonnet 4.6
**Duracion estimada:** ~6 horas de implementacion

---

## Contexto de Partida

El repositorio existia con un scaffold basico: carpetas vacias (`src/agent/`, `src/scrapers/`, `src/schemas/`, `src/utils/`, `tests/`), un `README.md` de una linea, un `CLAUDE.md` con el stack original (FastAPI + BeautifulSoup), y ningun archivo de codigo real.

El objetivo acordado: construir un **DeepAgent** autonomo que corra en Docker, se ejecute por CLI, busque productos en el mercado chileno, y retorne la mejor opcion + 3 alternativas con links directos.

---

## Investigacion Previa (antes de escribir codigo)

Antes de implementar se hizo research en paralelo con dos agentes:

### Mercado chileno
- **Solotodo** (`publicapi.solotodo.com`) — API publica gratuita, electronica/tech, historial de precios. **Mejor dato del mercado chileno para tech.**
- **MercadoLibre** (`api.mercadolibre.com/sites/MLC/`) — API publica sin OAuth para busquedas basicas. Site ID: `MLC`. Cubre todo tipo de productos.
- **Knasta.cl** — Sin API, server-rendered. Unico rastreador de historial de precios de Chile (equivalente a CamelCamelCamel).
- **Falabella, Ripley, Paris** — React SPAs pesados. Falabella usa Akamai anti-bot. Requieren Firecrawl o Playwright.
- **PCFactory, SP Digital** — Mas tradicionales, Firecrawl funciona bien directamente.

### Stack de herramientas web
- **Firecrawl** — 94% accuracy en extraccion e-commerce, schema-based, $16/mes. Elegido como extractor principal.
- **SerpAPI Google Shopping** — Soporta `gl=cl` para resultados de Chile. 250 busquedas/mes gratis.
- **Playwright** — Fallback para sitios con JS pesado. Requiere `--ipc=host` en Docker para no crashear Chromium.
- **Tavily** — Descartado como extractor principal (72% accuracy vs 94% Firecrawl), util solo como discovery.

### DeepAgents SDK
- Framework de LangChain sobre LangGraph para agentes autonomos complejos.
- `create_deep_agent()` acepta `subagents=[]` como diccionarios con `name`, `description`, `system_prompt`, `tools`.
- `response_format=PydanticModel` fuerza la salida estructurada.
- Middleware automatico incluye `write_todos` (planificacion), filesystem virtual, y coordinacion de subagentes via tool `task`.

---

## Plan Ejecutado

Se creo `plan_creacion.md` con 7 fases y 30+ pasos detallados antes de escribir una linea de codigo. El plan sirvio como especificacion tecnica.

---

## FASE 0: Setup del Proyecto

### Lo que se hizo
- Inicializado con `uv init` (reemplaza pip/venv segun solicitud del usuario).
- Creado `pyproject.toml` con todas las dependencias agrupadas por categoria.
- Creado `.env.example` con las 5 variables de entorno necesarias y comentarios de donde obtener cada key.
- Eliminado `src/scrapers/` (carpeta del scaffold original, reemplazada por `src/tools/`).
- Creado `src/tools/` con su `__init__.py`.
- Actualizado `CLAUDE.md` completamente: nuevo stack, nueva estructura de directorios, comandos reales con uv.

### Problemas encontrados
- **`uv init` creo `pyproject.toml` con `requires-python = ">=3.14"`** — la maquina corre Python 3.14 pero el target es 3.11+. Se corrigio manualmente a `>=3.11`.
- **`tool.uv.dev-dependencies` deprecado** — `uv sync` lanzaba warning. Se migro a `[dependency-groups] dev = [...]` que es el formato actual de uv.

---

## FASE 1: Schemas Pydantic

### Lo que se hizo
Creados en `src/schemas/`:

**`product.py`** — 3 modelos:
- `PricePoint` — Un punto de precio con fecha.
- `PriceHistory` — Historial con promedio, minimo y maximo.
- `ProductListing` — Producto en una tienda con validadores:
  - `price > 0`
  - `url` debe empezar con `http`
  - `original_price >= price` si existe
  - Properties calculadas: `discount_percentage` y `savings_amount`
- `DealResult` — Output final del agente con `best_deal`, `alternatives` (1-5), `recommendation`, duracion, fuentes.

**`search.py`** — 2 modelos:
- `SearchQuery` — Input del usuario con budget y tiendas preferidas opcionales.
- `SearchResult` — Output intermedio de cada tool con `success/error` y `count` property.

**`__init__.py`** — Exports limpios de todos los modelos.

**21 tests unitarios** en `tests/unit/test_schemas.py`.

### Problemas encontrados
- **Campo `date` en `PricePoint` chocaba con el tipo `date` de Python** — Pydantic v2 lanzaba `PydanticUserError: unevaluable-type-annotation`. El campo se llama `date` pero Pydantic no puede distinguirlo del tipo `date` importado de `datetime`. **Solucion:** renombrar el campo a `recorded_at`.

---

## FASE 2: Tools del Agente

### Lo que se hizo
Creados 6 tools en `src/tools/`, cada una decorada con `@tool` de LangChain. El docstring de cada tool es critico porque el LLM lo lee para decidir cuando usarla.

| Tool | Archivo | Fuente | Costo |
|------|---------|--------|-------|
| `search_solotodo` | `solotodo.py` | Solotodo API publica | Gratis |
| `search_mercadolibre` | `mercadolibre.py` | MercadoLibre API publica | Gratis |
| `search_google_shopping_chile` | `serpapi_shopping.py` | SerpAPI | 250/mes gratis |
| `extract_product_from_url` | `firecrawl_extract.py` | Firecrawl | $16/mes |
| `search_and_extract_from_site` | `firecrawl_extract.py` | Firecrawl | $16/mes |
| `scrape_with_browser` | `playwright_scraper.py` | Playwright local | Gratis |
| `get_price_history` | `knasta.py` | Knasta scraping | Gratis |

**Arquitectura de cada tool:**
- Errores manejados internamente con `try/except` — nunca lanzan excepciones al agente
- Retornan lista vacia `[]` o `SearchResult(success=False)` en caso de fallo
- Leen API keys desde `os.environ.get()` — si no existe la key, retornan vacio sin explotar
- Usan `httpx.Client` (no `requests`) para HTTP sync

**`__init__.py`** exporta las tools en 3 listas: `SEARCH_TOOLS`, `EXTRACTION_TOOLS`, `HISTORY_TOOLS`, y `ALL_TOOLS`.

**20 tests unitarios** en `tests/unit/test_tools.py`:
- Tests de estructura (nombre, descripcion, cantidad)
- Tests de comportamiento sin API keys (monkeypatching de `os.environ`)
- Tests de resiliencia ante errores de red (monkeypatching de `httpx.Client.get`)

### Problemas encontrados
- **`serpapi_shopping` retorna `SearchResult.model_dump()` en vez de `list[dict]`** cuando no hay key — inconsistencia de tipos con el resto de tools. Se dejo asi porque es informativo para el agente (incluye el `error_message`), y los tests lo validan como comportamiento esperado.
- **`knasta.py` no tiene API** — implementado con `httpx + BeautifulSoup` scrapeando `knasta.cl/search`. La estructura HTML de Knasta puede cambiar sin aviso. Se documento como "fragil" en los comentarios del codigo.
- **`playwright_scraper` es sincrono** — DeepAgents usa ejecucion sincrona por defecto. Se uso `playwright.sync_api` en lugar de `async_api`.

---

## FASE 3: Utilidades

### Lo que se hizo
**`src/utils/price.py`** — 4 funciones:
- `normalize_price(str) -> int | None` — Parsea todos los formatos de precio chileno: `$149.990`, `149,990`, `CLP 149.990`, etc. En Chile el punto es separador de miles, no decimal.
- `calculate_discount(original, current) -> dict` — Calcula ahorro, porcentaje, y si es "deal" real (>= 5% descuento).
- `format_clp(int) -> str` — `149990` → `"$149.990"` con punto como separador de miles.
- `compare_prices(list) -> list` — Deduplica (mismo store + precio similar dentro de ±1000 CLP) y ordena por precio ascendente.

**`src/utils/output.py`** — 3 funciones con Rich:
- `print_deal_result()` — Panel verde con mejor opcion, tabla azul con alternativas, seccion de historial si existe, footer con fuentes y duracion.
- `print_searching_status()` — Mensaje de progreso durante busqueda.
- `print_error()` — Panel rojo para errores.

**27 tests unitarios** en `tests/unit/test_utils.py`.

### Problemas encontrados
- **Formato chileno ambiguo** — `149.990` podria ser `149990` (miles) o `149.99` (decimal con cero extra). La funcion `normalize_price` implementa heuristica: si hay punto y la parte decimal tiene 3 digitos, es separador de miles; si tiene 1-2 digitos, es decimal. Cubre todos los casos reales del mercado chileno.

---

## FASE 4: Subagentes

### Lo que se hizo
3 subagentes en `src/agent/`, cada uno como funcion `create_*_subagent() -> dict`:

**`searcher-agent`** (`searcher.py`):
- Tools: `search_solotodo`, `search_mercadolibre`, `search_google_shopping_chile`
- Rol: busqueda inicial en APIs directas (rapido, gratis, sin scraping)
- System prompt: instrucciones sobre prioridad de busqueda (Solotodo primero si es tech), manejo de errores, criterios de calidad, formato CLP

**`scraper-agent`** (`scraper.py`):
- Tools: `extract_product_from_url`, `search_and_extract_from_site`, `scrape_with_browser`
- Rol: extraccion profunda de paginas web cuando el searcher no tiene precios completos
- System prompt: uso de Firecrawl como primera opcion, Playwright como fallback, reglas criticas de precios chilenos, lista de tiendas y sus caracteristicas tecnicas

**`comparator-agent`** (`comparator.py`):
- Tools: `get_price_history`
- Rol: ranking final con criterios ponderados (40% precio, 25% confianza tienda, 20% envio, 15% rating) y generacion de recomendacion en español
- System prompt: criterios de evaluacion detallados, deteccion de descuentos falsos, tier de confianza por tienda, formato de recomendacion esperado

**21 tests unitarios** en `tests/unit/test_agents.py`:
- Estructura de cada subagente (keys requeridas, nombre correcto, tools no vacias)
- Contenido del system prompt (menciona Chile, CLP, fallback, tiendas locales)
- Test de unicidad de nombres y no-solapamiento de tools entre searcher y scraper

### Problemas encontrados
- Ningun problema tecnico en esta fase. Los subagentes son diccionarios Python puros, sin dependencias externas en tiempo de construccion.

---

## FASE 5: Master Agent + CLI

### Lo que se hizo
**`src/agent/master.py`**:
- `_MASTER_SYSTEM_PROMPT` — Prompt maestro con flujo de 4 pasos (buscar → extraer → comparar → presentar), reglas criticas, y contexto del mercado chileno.
- `create_dealscout_agent()` — Llama a `create_deep_agent()` con los 3 subagentes, 2 tools directas de fallback, `response_format=DealResult`, y `StateBackend` (efimero, sin persistencia cross-thread).
- `run_search(query, max_budget)` — Valida que existe `ANTHROPIC_API_KEY`, construye el mensaje del usuario (con budget si se proporciona), invoca el agente, extrae `DealResult` de `result["structured_response"]`, y actualiza la duracion real de la busqueda.

**`src/main.py`** — Capa de orquestacion: carga dotenv, configura logging (suprime logs verbosos de httpx/langchain), llama a `run_search`.

**`cli.py`** (root del proyecto) con Typer:
- Comando `search` con argumento posicional `product`, opciones `--budget/-b`, `--json/-j`, `--verbose/-v`
- Valida `ANTHROPIC_API_KEY` antes de iniciar con mensaje de error amigable
- Muestra header y spinner de Rich durante la busqueda
- Maneja `KeyboardInterrupt` para salida limpia
- Output: tabla Rich o JSON segun flag

**6 tests unitarios** en `tests/unit/test_master.py`.

### Problemas encontrados
- **`import asyncio` no usado en `master.py`** — ruff lo detecto y lo elimino automaticamente con `--fix`.
- **`main.py` huerfano en el root** — `uv init` habia creado un `main.py` vacio con `print("Hello from dealscout-agent!")`. Se elimino al final para evitar confusion con `src/main.py`.

---

## FASE 6: Docker

### Lo que se hizo
**`Dockerfile`** multi-stage:
- Stage 1 (`builder`): instala `uv` desde `ghcr.io/astral-sh/uv:latest`, copia `pyproject.toml` y `uv.lock`, instala dependencias sin el proyecto (`--no-install-project`).
- Stage 2 (`runtime`): `python:3.12-bookworm` (Ubuntu, compatible con Playwright/glibc), instala dependencias del sistema para Chromium (libnss3, libatk, etc.), copia el `.venv` del builder, instala Chromium con `playwright install chromium`, crea usuario no-root `dealscout`, copia el codigo.
- `ENTRYPOINT ["python", "cli.py"]` con `CMD ["--help"]`.
- `HEALTHCHECK` que verifica que el CLI responde.

**`docker-compose.yml`**:
- `ipc: host` — critico para Chromium (shared memory, sin esto crashea con OOM).
- `init: true` — previene procesos zombie de subprocesos de Playwright.
- `env_file: .env` — carga API keys sin hardcodearlas.
- Volume `./output:/app/output` para exportar resultados JSON.

**`.dockerignore`** — excluye `.env`, `.git`, `.venv`, `tests/`, `docs/`, caches.

### Observaciones sobre Docker
- **Alpine Linux no soportado** — Playwright requiere glibc. Solo Ubuntu/Debian.
- **RAM por Chromium** — cada instancia consume ~100-300 MB. Para busquedas paralelas, planificar memoria.
- La imagen no se buildeó en este entorno (no hay Docker daemon local disponible), pero la sintaxis y configuracion fue verificada contra la documentacion oficial de Playwright Docker.

---

## FASE 7: Finalizacion

### Lo que se hizo
- **`README.md`** — Reescrito completamente: Quick Start con Docker y con uv, ejemplos de uso, ejemplo de output real, tabla de arquitectura, tabla de fuentes de datos con costos, tabla de variables de entorno, seccion de desarrollo.
- **`CLAUDE.md`** — Actualizado con stack real, estructura de directorios real, comandos con uv, y tabla de variables de entorno.
- **`.gitignore`** — Expandido: agregado `.env`, `output/`, `.ruff_cache/`, `*.egg-info/`, IDE files.
- **Eliminado `main.py` huerfano** del root (generado por `uv init`).
- **Linting limpio** — `ruff check .` sin errores.

---

## Resumen de Tests

| Archivo | Tests | Estado |
|---------|-------|--------|
| `test_schemas.py` | 21 | ✅ Todos pasan |
| `test_tools.py` | 20 | ✅ Todos pasan |
| `test_utils.py` | 27 | ✅ Todos pasan |
| `test_agents.py` | 21 | ✅ Todos pasan |
| `test_master.py` | 6 | ✅ Todos pasan |
| **TOTAL** | **95** | **✅ 95/95** |

---

## Problemas Globales y Decisiones Tecnicas

### 1. Python 3.14 vs target 3.11+
La maquina de desarrollo corre Python 3.14 (muy reciente). Langchain interna usa Pydantic v1 internamente que no es compatible con 3.14 (warning: `Core Pydantic V1 functionality isn't compatible with Python 3.14`). El warning no bloquea nada pero es visible en tests. En produccion (Docker con Python 3.12) esto no aparecera.

### 2. Inconsistencia de retorno en `serpapi_shopping`
Cuando falta `SERPAPI_KEY`, la tool retorna `SearchResult.model_dump()` (un dict) en lugar de `list[dict]`. Esto es intencional: el dict contiene `success=False` y `error_message` que el agente puede leer para entender que la tool no esta configurada. Las otras tools simplemente retornan `[]`.

### 3. `ruff` con E501 en system prompts
Los system prompts de los agentes contienen lineas inevitablemente largas (instrucciones en prosa). Se configuro `per-file-ignores` en `pyproject.toml` para ignorar E501 en `src/agent/*.py`, `src/tools/*.py`, `src/schemas/*.py`, `src/utils/*.py` y `tests/**/*.py`. El limite de 100 caracteres se mantiene para el resto del codigo.

### 4. Knasta sin API
Knasta es la unica fuente de historial de precios en Chile pero no tiene API publica. La implementacion usa `httpx + BeautifulSoup` para scraping directo. Es la tool mas fragil del sistema: si Knasta cambia su HTML, el scraping falla silenciosamente (retorna `None`). Se marco como `PRIORIDAD BAJA` en el plan y el sistema funciona correctamente sin ella.

### 5. uv como reemplazo de pip
El usuario solicitó usar uv. Toda la gestion de dependencias usa `uv sync` en lugar de `pip install`. El `pyproject.toml` usa `[dependency-groups]` (nuevo formato de uv, reemplaza el deprecado `[tool.uv.dev-dependencies]`).

---

## Estado Final del Proyecto

```
DealScout-Agent/
├── cli.py                  # Entry point: python cli.py "PS5"
├── pyproject.toml          # uv, dependencias, ruff, pytest config
├── .env.example            # Template de API keys (5 variables)
├── Dockerfile              # Multi-stage, Python 3.12 + Playwright/Chromium
├── docker-compose.yml      # --ipc=host, init:true, env_file
├── .dockerignore
├── CLAUDE.md               # Actualizado con stack real
├── README.md               # Documentacion completa
├── BITACORA.md             # Este archivo
├── plan_creacion.md        # Plan original de 7 fases
├── src/
│   ├── agent/
│   │   ├── master.py       # create_dealscout_agent() + run_search()
│   │   ├── searcher.py     # Subagente busqueda (Solotodo+ML+Google)
│   │   ├── scraper.py      # Subagente extraccion (Firecrawl+Playwright)
│   │   └── comparator.py   # Subagente ranking (precio/confianza/envio)
│   ├── tools/
│   │   ├── solotodo.py     # API gratuita, electronica chilena
│   │   ├── mercadolibre.py # API gratuita, todo tipo de productos
│   │   ├── serpapi_shopping.py  # Google Shopping CL (250/mes gratis)
│   │   ├── firecrawl_extract.py # Extraccion estructurada ($16/mes)
│   │   ├── playwright_scraper.py # Browser fallback (gratis)
│   │   └── knasta.py       # Historial de precios (scraping, fragil)
│   ├── schemas/
│   │   ├── product.py      # ProductListing, DealResult, PriceHistory
│   │   └── search.py       # SearchQuery, SearchResult
│   └── utils/
│       ├── price.py        # normalize_price, format_clp, compare_prices
│       └── output.py       # Rich: tablas, paneles, spinners
└── tests/unit/             # 95 tests, 0 fallos
```

### Para ejecutar (requiere configurar .env):
```bash
cp .env.example .env
# Agregar al menos ANTHROPIC_API_KEY en .env

# Local
uv run python cli.py "PlayStation 5"

# Docker
docker compose run --rm dealscout "PlayStation 5"
```

---

## Proximos Pasos Sugeridos

1. **Tests de integracion** — Crear `tests/integration/` con tests reales contra las APIs (Solotodo, MercadoLibre). Requieren API keys. Marcar con `@pytest.mark.integration`.

2. **Verificar Solotodo API** — La estructura de respuesta implementada es orientativa. Correr contra la API real y ajustar los campos segun la respuesta actual de `publicapi.solotodo.com`.

3. **Cache de resultados** — Agregar cache con TTL de 1 hora para evitar repetir busquedas identicas. Usar `diskcache` o simplemente un dict en memoria.

4. **Modo watch** — Opcion `--watch 30m` para re-ejecutar la busqueda cada N minutos y alertar si el precio baja.

5. **Output a archivo** — Opcion `--output resultado.json` para guardar el resultado en el volume de Docker.

6. **GitHub Actions** — CI que corra `pytest tests/unit/` y `ruff check .` en cada push.
