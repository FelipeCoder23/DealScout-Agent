# Plan de Creacion - DealScout Agent

## Contexto General

DealScout es un DeepAgent (SDK de LangChain sobre LangGraph) que corre en Docker y se ejecuta por CLI. Su objetivo: recibir el nombre de un producto, buscar en el mercado chileno, y devolver la mejor opcion + 3 alternativas con links, precios e informacion relevante.

**Documentacion de referencia obligatoria antes de implementar:**
- `docs/LANGGRAPH_GUIDE.md` — API completa de DeepAgents (create_deep_agent, subagentes, backends, middleware, schemas)
- `docs/WEB_BROWSING_RESEARCH.md` — Investigacion de herramientas web, APIs chilenas, Docker, costos

**Reglas de codigo (de CLAUDE.md):**
- Python 3.11+ con tipado estricto (Type Hints en todo)
- Conventional commits (feat:, fix:, refactor:)
- Docstrings en funciones principales
- Tests obligatorios para tools y logica de agente
- Linting con Ruff / Black

---

## FASE 0: Setup del Proyecto

### Paso 0.1 — Archivo de dependencias `requirements.txt`

Crear `requirements.txt` en el root con estas dependencias (fijar versiones):

**Dependencias core:**
- `deepagents` — SDK del agente
- `langchain` — base de LangChain
- `langgraph` — runtime de ejecucion
- `langchain-anthropic` — provider de Claude
- `langchain-community` — toolkit de Playwright

**Dependencias de tools:**
- `tavily-python` — busqueda web
- `firecrawl-py` — extraccion estructurada de paginas web
- `google-search-results` — paquete de SerpAPI para Google Shopping
- `httpx` — cliente HTTP async para APIs (Solotodo, MercadoLibre)
- `playwright` — navegador headless para fallback en sitios JS pesados

**Dependencias de schemas/validacion:**
- `pydantic>=2.0` — validacion de datos y schemas de salida

**Dependencias CLI:**
- `typer[all]` — framework CLI con colores y rich output
- `rich` — tablas bonitas, colores, spinners en terminal

**Dependencias de desarrollo:**
- `pytest` y `pytest-asyncio` — testing
- `ruff` — linting
- `python-dotenv` — cargar .env

### Paso 0.2 — Archivo `.env.example`

Crear `.env.example` en el root con las variables de entorno necesarias. Cada variable con un comentario explicando donde obtener la API key:

```
ANTHROPIC_API_KEY=       # https://console.anthropic.com/
TAVILY_API_KEY=          # https://tavily.com/ (free tier: 1000 credits/mes)
SERPAPI_KEY=             # https://serpapi.com/ (free tier: 250 busquedas/mes)
FIRECRAWL_API_KEY=       # https://firecrawl.dev/ ($16/mes hobby)
MERCADOLIBRE_ACCESS_TOKEN=  # https://developers.mercadolibre.cl/ (opcional, OAuth)
```

### Paso 0.3 — Reestructurar directorios

La estructura actual tiene `src/scrapers/`. Renombrar y crear los directorios que faltan para que quede asi:

```
src/
├── __init__.py            (ya existe)
├── main.py                (ya existe, se reescribira en Fase 5)
├── agent/
│   ├── __init__.py        (ya existe)
│   ├── master.py          (crear)
│   ├── searcher.py        (crear)
│   ├── scraper.py         (crear)
│   └── comparator.py      (crear)
├── tools/                 (CREAR este directorio, reemplaza a scrapers/)
│   ├── __init__.py
│   ├── solotodo.py
│   ├── mercadolibre.py
│   ├── serpapi_shopping.py
│   ├── firecrawl_extract.py
│   ├── playwright_scraper.py
│   └── knasta.py
├── schemas/
│   ├── __init__.py        (ya existe)
│   ├── product.py         (crear)
│   └── search.py          (crear)
└── utils/
    ├── __init__.py        (ya existe)
    ├── price.py           (crear)
    └── output.py          (crear)
```

Eliminar `src/scrapers/` (vacio, ya no se usa). Crear `src/tools/` con su `__init__.py`.

Tambien crear `cli.py` en el root del proyecto (entry point principal).

### Paso 0.4 — Actualizar CLAUDE.md

Actualizar el archivo CLAUDE.md para reflejar el stack real:
- Cambiar "FastAPI" por "CLI con Typer"
- Cambiar "Playwright / BeautifulSoup" por "DeepAgents SDK + Firecrawl + Playwright fallback"
- Cambiar "LangGraph / LangChain" por "DeepAgents SDK (sobre LangGraph/LangChain)"
- Agregar las variables de entorno reales
- Actualizar la estructura de directorios
- Agregar comando CLI: `python cli.py "nombre del producto"`

---

## FASE 1: Schemas Pydantic

Esta fase es la base. Todo lo que viene despues depende de estos schemas. No usar herramientas externas aqui, solo Pydantic puro.

### Paso 1.1 — `src/schemas/product.py`

Definir los siguientes modelos Pydantic v2 (usar `BaseModel` de pydantic):

**`ProductListing`** — Representa UN producto encontrado en UNA tienda:
- `name: str` — nombre del producto tal como aparece en la tienda
- `price: int` — precio en CLP (pesos chilenos, siempre entero, sin decimales)
- `currency: str` — siempre "CLP", valor por defecto
- `store: str` — nombre de la tienda (ej: "Falabella", "MercadoLibre", "PCFactory")
- `url: str` — URL directa al producto en la tienda (el usuario debe poder hacer click y llegar al producto)
- `in_stock: bool` — si esta disponible, default True
- `original_price: int | None` — precio original antes de descuento (None si no hay descuento)
- `shipping_info: str | None` — info de envio si esta disponible (ej: "Envio gratis", "Despacho en 3-5 dias")
- `rating: float | None` — rating del producto (0.0-5.0)
- `review_count: int | None` — cantidad de reviews
- `image_url: str | None` — URL de la imagen del producto
- `source: str` — de donde se obtuvo el dato: "solotodo_api", "mercadolibre_api", "serpapi", "firecrawl", "playwright"
- `scraped_at: datetime` — timestamp de cuando se obtuvo el dato, auto-generar con `default_factory=datetime.now`

Agregar un `model_validator` que valide:
- `price` debe ser mayor a 0
- Si `original_price` existe, debe ser mayor o igual a `price`
- `url` debe empezar con "http"

**`PriceHistory`** — Historial de precio de un producto:
- `product_name: str`
- `store: str`
- `prices: list[PricePoint]` — lista de puntos de precio
- `average_price: int` — precio promedio calculado
- `lowest_price: int` — precio mas bajo historico
- `highest_price: int` — precio mas alto historico

**`PricePoint`** — Un punto de precio en el tiempo:
- `price: int`
- `date: date`

**`DealResult`** — El resultado final que devuelve el agente:
- `query: str` — la busqueda original del usuario
- `best_deal: ProductListing` — la mejor opcion recomendada
- `alternatives: list[ProductListing]` — exactamente 3 alternativas, usar `Field(min_length=1, max_length=5)`
- `price_history: PriceHistory | None` — historial si se pudo obtener
- `recommendation: str` — texto explicativo de por que esa es la mejor opcion (2-3 oraciones)
- `total_results_found: int` — cuantos resultados se encontraron en total antes de filtrar
- `sources_consulted: list[str]` — lista de fuentes consultadas (ej: ["Solotodo API", "MercadoLibre API", "Falabella via Firecrawl"])
- `search_duration_seconds: float` — cuanto tardo la busqueda total
- `searched_at: datetime`

### Paso 1.2 — `src/schemas/search.py`

**`SearchQuery`** — Lo que el usuario pide:
- `product_name: str` — nombre del producto a buscar
- `max_budget: int | None` — presupuesto maximo en CLP (opcional)
- `preferred_stores: list[str]` — tiendas preferidas (default: lista vacia = todas)
- `category: str | None` — categoria del producto (ej: "electronica", "hogar", "deportes")

**`SearchResult`** — Resultado intermedio de un tool de busqueda:
- `listings: list[ProductListing]` — productos encontrados
- `source: str` — de que tool vino este resultado
- `raw_query: str` — la query que se uso para buscar
- `success: bool` — si la busqueda fue exitosa
- `error_message: str | None` — mensaje de error si fallo

### Paso 1.3 — `src/schemas/__init__.py`

Exportar todos los modelos desde el `__init__.py` para imports limpios:
`from src.schemas import ProductListing, DealResult, SearchQuery, SearchResult, PriceHistory`

### Paso 1.4 — Tests de schemas

Crear `tests/unit/test_schemas.py`:

- Test que `ProductListing` rechaza precio negativo o cero
- Test que `ProductListing` rechaza `original_price` menor que `price`
- Test que `ProductListing` rechaza URL sin "http"
- Test que `DealResult` se crea correctamente con datos validos
- Test que `SearchQuery` funciona con valores minimos (solo `product_name`)
- Test de serializacion/deserializacion JSON de `DealResult` (model_dump_json / model_validate_json)

---

## FASE 2: Tools (Herramientas del Agente)

Cada tool es una funcion decorada con `@tool` de LangChain. El docstring de cada funcion es CRITICO porque es lo que el LLM lee para decidir cuando usarla. Cada tool debe:
- Tener type hints completos en parametros y retorno
- Retornar `list[ProductListing]` o `SearchResult`
- Manejar errores internamente (try/except) y retornar lista vacia o SearchResult con `success=False` en caso de fallo, NUNCA lanzar excepciones no manejadas
- Usar `httpx.AsyncClient` para llamadas HTTP (no requests)
- Leer API keys desde variables de entorno con `os.environ.get()`

### Paso 2.1 — `src/tools/solotodo.py` (PRIORIDAD ALTA)

**Tool: `search_solotodo`**

Esta es la tool mas importante porque Solotodo tiene API publica gratuita y datos excelentes de electronica chilena.

**Docstring:** "Busca productos de tecnologia y electronica en Solotodo.cl. Ideal para laptops, celulares, GPUs, monitores, componentes de PC, y electrodomesticos. Retorna precios actuales de multiples tiendas chilenas con links directos. NO usar para ropa, comida, o productos no tecnologicos."

**Parametros:**
- `query: str` — nombre del producto a buscar
- `max_results: int = 10` — cuantos resultados maximo

**Implementacion:**
1. Hacer GET a `https://publicapi.solotodo.com/products/?search={query}&page_size={max_results}`
2. Para cada producto en la respuesta, extraer los campos del JSON y mapear a `ProductListing`
3. La API de Solotodo retorna productos con multiples "entities" (una por tienda). Cada entity es un ProductListing separado
4. Mapear campos de Solotodo a ProductListing:
   - `entity.active_registry.offer_price` → `price`
   - `entity.store.name` → `store`
   - `entity.external_url` → `url`
   - `product.name` → `name`
   - `source` = "solotodo_api"
5. Si la API falla o no hay resultados, retornar lista vacia

**NOTA IMPORTANTE:** Antes de implementar, consultar la documentacion actualizada de la API de Solotodo en `https://publicapi.solotodo.com/` para verificar los endpoints y estructura de respuesta exacta. La estructura de campos descrita arriba es orientativa; el implementador debe adaptarse a la respuesta real de la API.

### Paso 2.2 — `src/tools/mercadolibre.py` (PRIORIDAD ALTA)

**Tool: `search_mercadolibre`**

**Docstring:** "Busca productos en MercadoLibre Chile. Cubre practicamente cualquier categoria: electronica, hogar, ropa, deportes, vehiculos, etc. Es el marketplace mas grande de Chile. Retorna precios, vendedores y links directos."

**Parametros:**
- `query: str` — nombre del producto
- `max_results: int = 10`
- `price_min: int | None = None` — filtro de precio minimo en CLP
- `price_max: int | None = None` — filtro de precio maximo en CLP

**Implementacion:**
1. MercadoLibre tiene API publica que NO requiere OAuth para busquedas basicas
2. Endpoint: `GET https://api.mercadolibre.com/sites/MLC/search?q={query}&limit={max_results}`
   - `MLC` es el site_id de Chile
   - Se puede agregar `&price={min}-{max}` para filtrar por precio
3. Mapear campos de la respuesta JSON a `ProductListing`:
   - `item.title` → `name`
   - `item.price` → `price` (ya viene en CLP como entero)
   - `item.permalink` → `url`
   - `item.seller.nickname` o `"MercadoLibre"` → `store`
   - `item.shipping.free_shipping` → mapear a `shipping_info`
   - `item.thumbnail` → `image_url`
   - `item.condition` puede ser "new" o "used", filtrar solo "new" por defecto
   - `source` = "mercadolibre_api"
4. Manejar paginacion si es necesario

### Paso 2.3 — `src/tools/serpapi_shopping.py` (PRIORIDAD MEDIA)

**Tool: `search_google_shopping_chile`**

**Docstring:** "Busca productos en Google Shopping enfocado en Chile. Util para descubrir tiendas y precios que no estan en Solotodo o MercadoLibre. Cubre amplia variedad de tiendas chilenas (Falabella, Ripley, Paris, PCFactory, etc). Usar como complemento a las busquedas en APIs directas."

**Parametros:**
- `query: str` — nombre del producto
- `max_results: int = 10`

**Implementacion:**
1. Requiere `SERPAPI_KEY` del entorno
2. Si la key no existe, retornar SearchResult con success=False y error explicando que falta la key
3. Usar la clase `GoogleSearch` del paquete `google-search-results` (serpapi):
   - `engine`: "google_shopping"
   - `q`: query
   - `location`: "Chile"
   - `gl`: "cl"
   - `hl`: "es"
   - `num`: max_results
4. Mapear `shopping_results` a `ProductListing`:
   - `result.title` → `name`
   - `result.extracted_price` → `price` (convertir a int, ya que Google Shopping devuelve float)
   - `result.product_link` o `result.link` → `url`
   - `result.source` → `store`
   - `result.rating` → `rating`
   - `result.reviews` → `review_count`
   - `result.thumbnail` → `image_url`
   - `source` = "serpapi"

### Paso 2.4 — `src/tools/firecrawl_extract.py` (PRIORIDAD MEDIA)

**Tool: `extract_product_from_url`**

**Docstring:** "Extrae informacion estructurada de un producto desde una URL de tienda chilena. Usa Firecrawl para renderizar JavaScript y extraer datos. Ideal para URLs de Falabella, Ripley, Paris, PCFactory, SP Digital, y cualquier tienda con paginas de producto. Pasarle la URL directa del producto."

**Parametros:**
- `url: str` — URL directa de la pagina del producto
- `store_name: str = "Unknown"` — nombre de la tienda (para el campo store)

**Implementacion:**
1. Requiere `FIRECRAWL_API_KEY` del entorno
2. Si la key no existe, retornar lista vacia
3. Usar `FirecrawlApp` del paquete `firecrawl-py`
4. Llamar al metodo `scrape_url` con el parametro `extract` que recibe un JSON schema
5. El JSON schema debe definir los campos que queremos extraer: nombre del producto, precio, precio original, disponibilidad, envio, rating
6. Mapear la respuesta extraida a `ProductListing`:
   - `source` = "firecrawl"
   - `url` = la URL que se paso como parametro
   - `store` = store_name
7. Manejar el caso de que Firecrawl no pueda acceder a la pagina (403, timeout, etc)

**Tool: `search_and_extract_from_site`**

**Docstring:** "Busca un producto en un sitio web especifico y extrae resultados. Util cuando quieres buscar directamente en Falabella.com, Ripley.cl, etc. Primero busca en el sitio, luego extrae datos de los resultados."

**Parametros:**
- `query: str` — nombre del producto
- `site_url: str` — dominio base del sitio (ej: "falabella.com", "ripley.cl")
- `max_results: int = 5`

**Implementacion:**
1. Usar Firecrawl `search` con el query y `site:{site_url}` como filtro
2. De los resultados, tomar los primeros `max_results` URLs
3. Para cada URL, llamar a `extract_product_from_url`
4. Retornar la lista combinada de ProductListing

### Paso 2.5 — `src/tools/knasta.py` (PRIORIDAD BAJA)

**Tool: `get_price_history`**

**Docstring:** "Consulta el historial de precios de un producto en Knasta.cl. Knasta es el principal rastreador de precios de Chile, similar a CamelCamelCamel. Retorna precios historicos de los ultimos 90 dias. Usar solo despues de haber encontrado el producto en otras fuentes, para validar si el precio actual es bueno."

**Parametros:**
- `product_name: str` — nombre del producto para buscar en Knasta
- `product_url: str | None = None` — URL del producto si se conoce (Knasta a veces indexa por URL)

**Implementacion:**
1. Knasta no tiene API publica, se debe scrape
2. Usar Firecrawl o httpx para acceder a `https://knasta.cl/search?q={product_name}`
3. Parsear los resultados de busqueda y encontrar el match mas cercano
4. Acceder a la pagina del producto y extraer los datos del historial de precios
5. Knasta renderiza server-side, asi que httpx + BeautifulSoup deberia funcionar sin Playwright
6. Retornar `PriceHistory` con los datos extraidos
7. Si falla o no encuentra el producto, retornar None

**Esta tool es la de menor prioridad. Si el tiempo es limitado, implementar un stub que retorne None y marcar como TODO.**

### Paso 2.6 — `src/tools/playwright_scraper.py` (PRIORIDAD BAJA)

**Tool: `scrape_with_browser`**

**Docstring:** "Navega a una URL con un navegador completo (Chromium) y extrae el contenido de la pagina. Usar SOLO como fallback cuando Firecrawl no puede acceder a un sitio (error 403, contenido bloqueado). Este tool es mas lento y costoso en recursos."

**Parametros:**
- `url: str` — URL a navegar
- `extract_selector: str | None = None` — CSS selector opcional para extraer contenido especifico

**Implementacion:**
1. Usar `playwright.async_api` para crear browser en modo headless
2. Navegar a la URL con `page.goto(url, wait_until="networkidle")`
3. Si se proporciona `extract_selector`, usar `page.query_selector_all(selector)` para extraer elementos
4. Si no, usar `page.content()` para obtener el HTML completo
5. Retornar el contenido como string (el LLM o un paso posterior lo parseara)
6. Importante: usar timeout de 30 segundos, cerrar browser siempre en un finally block
7. Configurar user-agent realista y viewport de desktop

**Esta tool es un fallback. No es subagente, es una herramienta simple que retorna HTML/texto crudo.**

### Paso 2.7 — `src/tools/__init__.py`

Exportar todas las tools en una lista conveniente:

Definir una variable `ALL_TOOLS` que contenga la lista de todas las funciones tool.
Definir `SEARCH_TOOLS` (solotodo, mercadolibre, serpapi) y `EXTRACTION_TOOLS` (firecrawl, playwright) como sublistas para que los subagentes puedan importar solo lo que necesitan.

### Paso 2.8 — Tests de tools

Crear `tests/unit/test_tools.py`:

- Para cada tool, crear un test que verifique que se puede instanciar y que tiene el nombre y descripcion correctos (las tools de LangChain tienen `.name` y `.description`)
- Crear tests de integracion en `tests/integration/test_tools_live.py` (marcados con `@pytest.mark.integration` para no correrlos en CI sin API keys):
  - Test que `search_solotodo("notebook")` retorna al menos 1 resultado
  - Test que `search_mercadolibre("iphone")` retorna al menos 1 resultado
  - Test que cada ProductListing retornado tiene URL valida y precio > 0

---

## FASE 3: Utilidades

### Paso 3.1 — `src/utils/price.py`

**Funciones a implementar:**

**`normalize_price(price_str: str) -> int`**
- Convierte strings de precio chileno a entero
- Debe manejar formatos: "$149.990", "149990", "$149,990", "CLP 149.990", "149.990 CLP"
- En Chile el punto es separador de miles (NO decimal)
- Remover caracteres no numericos excepto el punto de miles
- Retornar entero

**`calculate_discount(original: int, current: int) -> dict`**
- Calcula descuento entre precio original y actual
- Retorna dict con: `amount` (cuanto se ahorra), `percentage` (% de descuento), `is_deal` (True si descuento > 5%)

**`format_clp(price: int) -> str`**
- Formatea un entero como precio chileno: 149990 → "$149.990"
- Usar punto como separador de miles

**`compare_prices(listings: list[ProductListing]) -> list[ProductListing]`**
- Recibe lista de ProductListing
- Elimina duplicados (mismo producto en misma tienda)
- Ordena por precio ascendente
- Retorna la lista ordenada y deduplicada

### Paso 3.2 — `src/utils/output.py`

**Funciones a implementar usando la libreria `rich`:**

**`print_deal_result(result: DealResult) -> None`**
- Imprime el resultado final en terminal con formato bonito
- Usar `rich.console.Console` para colores
- Usar `rich.table.Table` para la tabla de alternativas
- Formato esperado:

```
[bold green]MEJOR OPCION[/]
  {nombre del producto}
  {precio formateado} en {tienda}
  Link: {url}
  {info de envio} | {rating} | {info de descuento si aplica}

[bold blue]ALTERNATIVAS[/]
  (tabla con columnas: #, Tienda, Precio, Link)

[dim]HISTORIAL[/] (si existe)
  Precio promedio ultimos 90 dias: {promedio}
  Estas ahorrando {diferencia} vs promedio

Fuentes consultadas: {lista de fuentes}
Busqueda completada en {duracion} segundos
```

**`print_searching_status(message: str) -> None`**
- Imprime un mensaje de estado con spinner animado usando `rich.status.Status`
- Para dar feedback al usuario mientras el agente trabaja

**`print_error(message: str) -> None`**
- Imprime un mensaje de error en rojo

### Paso 3.3 — Tests de utils

Crear `tests/unit/test_utils.py`:

- Test `normalize_price` con todos los formatos chilenos: "$149.990", "149990", "$149,990"
- Test `calculate_discount` con descuento real y sin descuento
- Test `format_clp` formatea correctamente
- Test `compare_prices` elimina duplicados y ordena

---

## FASE 4: Subagentes

Cada subagente se define como un diccionario segun la API de DeepAgents (ver `docs/LANGGRAPH_GUIDE.md` seccion "Subagentes"). Cada subagente tiene su propio archivo para mantener responsabilidades claras.

### Paso 4.1 — `src/agent/searcher.py`

**Rol:** Descubrimiento de productos. Busca en multiples fuentes y retorna URLs y datos preliminares.

**Definir una funcion `create_searcher_subagent() -> dict`** que retorne el diccionario del subagente:

- `name`: "searcher-agent"
- `description`: "Busca productos en multiples fuentes del mercado chileno. Usa APIs de Solotodo, MercadoLibre, y Google Shopping Chile para encontrar donde se vende un producto y a que precios. Delegale la busqueda inicial de productos."
- `system_prompt`: Prompt detallado que le indique:
  1. Tu rol es buscar un producto en el mercado chileno usando las herramientas disponibles
  2. SIEMPRE empezar por Solotodo si el producto es de tecnologia/electronica
  3. SIEMPRE buscar en MercadoLibre sin importar la categoria
  4. Usar Google Shopping Chile como complemento para descubrir tiendas adicionales
  5. Para cada resultado, asegurar que tienes: nombre exacto, precio en CLP, URL directa, nombre de la tienda
  6. Filtrar resultados duplicados y productos que no coincidan con la busqueda
  7. Si una herramienta falla, continuar con las otras sin detenerse
  8. Retornar TODOS los resultados encontrados, sin filtrar por precio (eso lo hace otro agente)
- `tools`: Lista con las funciones `search_solotodo`, `search_mercadolibre`, `search_google_shopping_chile`
- NO especificar `model` (hereda del master)

### Paso 4.2 — `src/agent/scraper.py`

**Rol:** Extraccion profunda. Cuando el Searcher encuentra URLs de tiendas pero sin datos completos, el Scraper va a esas paginas y extrae informacion detallada.

**Definir una funcion `create_scraper_subagent() -> dict`** que retorne:

- `name`: "scraper-agent"
- `description`: "Extrae informacion detallada de productos desde URLs de tiendas chilenas (Falabella, Ripley, Paris, PCFactory, etc). Delegale cuando tienes la URL de un producto pero necesitas extraer precio, disponibilidad, o detalles adicionales."
- `system_prompt`: Prompt que indique:
  1. Tu rol es ir a URLs de tiendas y extraer datos estructurados del producto
  2. Usar Firecrawl como primera opcion para extraer datos
  3. Si Firecrawl falla (403, timeout), usar Playwright como fallback
  4. Extraer: nombre completo del producto, precio actual en CLP, precio original (si hay descuento), disponibilidad, info de envio, rating
  5. Los precios chilenos usan punto como separador de miles (ej: $149.990 = ciento cuarenta y nueve mil novecientos noventa pesos)
  6. Devolver los datos en formato estructurado
  7. Si no puedes acceder a una pagina despues de intentar ambos metodos, reportar el error y continuar
- `tools`: Lista con `extract_product_from_url`, `search_and_extract_from_site`, `scrape_with_browser`
- NO especificar `model`

### Paso 4.3 — `src/agent/comparator.py`

**Rol:** Analisis y recomendacion. Recibe todos los productos encontrados, los analiza, y genera la recomendacion final.

**Definir una funcion `create_comparator_subagent() -> dict`** que retorne:

- `name`: "comparator-agent"
- `description`: "Analiza y compara productos encontrados para determinar la mejor opcion de compra. Delegale cuando ya tienes una lista de productos con precios de multiples tiendas y necesitas la recomendacion final."
- `system_prompt`: Prompt que indique:
  1. Tu rol es analizar una lista de productos del mercado chileno y recomendar el mejor deal
  2. Criterios de evaluacion (en orden de importancia):
     a. Precio mas bajo (ponderacion: 40%)
     b. Confiabilidad de la tienda (ponderacion: 25%) - tiendas grandes como Falabella, Ripley, MercadoLibre son mas confiables que vendedores desconocidos
     c. Disponibilidad inmediata y envio (ponderacion: 20%) - preferir envio gratis y despacho rapido
     d. Reviews y rating del producto (ponderacion: 15%)
  3. Si hay historial de precios disponible (de Knasta), usarlo para validar si el precio actual es realmente bueno o es el precio normal
  4. Detectar "descuentos falsos" donde el precio original esta inflado artificialmente
  5. Devolver: la mejor opcion con justificacion, y exactamente 3 alternativas
  6. La recomendacion debe ser en espanol, directa y util (ej: "El mejor precio esta en MercadoLibre, $40.000 menos que Falabella. El vendedor tiene 98% de reputacion positiva y envio gratis.")
- `tools`: Lista con `get_price_history` (de Knasta)
- NO especificar `model`

### Paso 4.4 — Tests de subagentes

Crear `tests/unit/test_agents.py`:

- Test que `create_searcher_subagent()` retorna un dict con keys requeridas: "name", "description", "system_prompt", "tools"
- Test que cada subagente tiene tools asignadas (no lista vacia)
- Test que los system_prompts contienen instrucciones sobre Chile/CLP (para verificar que no se olvido el contexto local)

---

## FASE 5: Master Agent + CLI

### Paso 5.1 — `src/agent/master.py`

**Definir una funcion `create_dealscout_agent()`** que retorne el agente principal creado con `create_deep_agent`.

**Parametros de create_deep_agent:**

- `name`: "dealscout"
- `model`: `"anthropic:claude-sonnet-4-6"` (leer de env `DEALSCOUT_MODEL` con este como default)
- `tools`: Lista con `search_solotodo`, `search_mercadolibre` (tools directas del master como fallback)
- `subagents`: Lista con los 3 subagentes creados por las funciones del Paso 4
- `system_prompt`: Prompt maestro detallado:
  1. "Eres DealScout, un agente experto en encontrar las mejores ofertas de productos en el mercado chileno."
  2. "Cuando el usuario pide buscar un producto, sigue este flujo:"
     - Paso 1: Delega la busqueda al searcher-agent para descubrir productos y precios en APIs (Solotodo, MercadoLibre, Google Shopping Chile)
     - Paso 2: Si el searcher encuentra URLs de tiendas (Falabella, Ripley, Paris) sin precios, delega al scraper-agent para extraer datos detallados
     - Paso 3: Una vez que tienes resultados de multiples fuentes, delega al comparator-agent para analizar y generar la recomendacion
     - Paso 4: Presenta el resultado final al usuario
  3. "REGLAS IMPORTANTES:"
     - Todos los precios son en pesos chilenos (CLP), enteros, sin decimales
     - Siempre incluir links directos a los productos
     - Si un subagente falla, intentar cumplir el objetivo con los datos parciales que tengas
     - Minimo debes consultar 2 fuentes diferentes antes de dar una recomendacion
     - El resultado final DEBE incluir: mejor opcion + 3 alternativas
  4. "TIENDAS DEL MERCADO CHILENO (de mayor a menor confianza):"
     - Tier 1: Falabella, MercadoLibre, Ripley, Paris
     - Tier 2: PCFactory, SP Digital, Sodimac, Hites
     - Tier 3: Corona, ABCDIN, Microplay, Zmart
- `backend`: `StateBackend` (efimero, no necesitamos persistencia entre ejecuciones)
- `response_format`: `DealResult` (el schema Pydantic de la Fase 1)

**Definir tambien una funcion `async def run_search(query: str, max_budget: int | None = None) -> DealResult`:**
1. Crear el agente con `create_dealscout_agent()`
2. Construir el mensaje del usuario con el query (y presupuesto si se proporciono)
3. Invocar el agente con `agent.invoke({"messages": [{"role": "user", "content": mensaje}]})`
4. Extraer el `DealResult` de `result["structured_response"]`
5. Retornar el `DealResult`

### Paso 5.2 — `src/main.py`

Reescribir `src/main.py` como modulo de ejecucion:

- Importar `run_search` de `src.agent.master`
- Definir `async def main(query: str, budget: int | None = None) -> DealResult`
- Que cargue dotenv, configure logging basico, y llame a `run_search`

### Paso 5.3 — `cli.py` (entry point)

Crear `cli.py` en el root del proyecto usando `typer`:

**Comando principal: `search`**
- Argumento posicional: `product` (str) — nombre del producto a buscar
- Opcion `--budget` / `-b` (int, opcional) — presupuesto maximo en CLP
- Opcion `--json` / `-j` (bool, default False) — output en JSON en lugar de formato rich
- Opcion `--verbose` / `-v` (bool, default False) — mostrar logs de progreso

**Flujo del comando:**
1. Validar que al menos `ANTHROPIC_API_KEY` esta configurada, si no, imprimir error y salir
2. Mostrar mensaje "Buscando: {product}..." con spinner de rich
3. Llamar a `asyncio.run(main(product, budget))`
4. Si `--json`, imprimir `result.model_dump_json(indent=2)`
5. Si no, llamar a `print_deal_result(result)` de `src/utils/output.py`
6. Manejar KeyboardInterrupt para salida limpia
7. Manejar excepciones generales con mensaje de error amigable

**Ejemplo de uso:**
```bash
python cli.py "PlayStation 5"
python cli.py "iPhone 15 128gb" --budget 800000
python cli.py "notebook gamer" --json
```

### Paso 5.4 — Tests del master agent

Crear `tests/unit/test_master.py`:

- Test que `create_dealscout_agent()` retorna un objeto con metodo `invoke`
- Test que el system_prompt contiene "chileno" y "CLP"
- Test que tiene exactamente 3 subagentes configurados

---

## FASE 6: Docker

### Paso 6.1 — `Dockerfile`

Crear Dockerfile multi-stage:

**Stage 1: base**
- `FROM python:3.12-bookworm`
- Instalar dependencias del sistema para Playwright/Chromium
- Instalar Playwright y descargar solo Chromium: `playwright install --with-deps chromium`
- Crear usuario no-root llamado `dealscout`

**Stage 2: app**
- Copiar `requirements.txt` e instalar dependencias Python
- Copiar todo el codigo fuente
- Establecer `WORKDIR /app`
- Cambiar a usuario `dealscout` (no correr como root)
- `ENTRYPOINT ["python", "cli.py"]`
- `CMD ["--help"]` (si se corre sin argumentos, muestra la ayuda)

**Variables de entorno necesarias (documentar en el Dockerfile con ENV pero sin valores):**
- `ANTHROPIC_API_KEY`
- `TAVILY_API_KEY`
- `SERPAPI_KEY`
- `FIRECRAWL_API_KEY`

### Paso 6.2 — `docker-compose.yml`

Crear docker-compose.yml simple para desarrollo:

**Servicio `dealscout`:**
- build desde el Dockerfile local
- `ipc: host` (necesario para Chromium)
- `init: true` (prevenir procesos zombie)
- `env_file: .env` (cargar variables de entorno)
- Sin puertos expuestos (es CLI, no servidor)
- Volume opcional de `/app/output` para exportar resultados JSON

**Documentar el uso:**
```bash
docker compose run dealscout "PlayStation 5"
docker compose run dealscout "notebook gamer" --budget 700000 --json
```

### Paso 6.3 — `.dockerignore`

Crear `.dockerignore` que excluya:
- `.git/`
- `.env`
- `__pycache__/`
- `.venv/`
- `*.pyc`
- `docs/`
- `tests/`
- `.ruff_cache/`

### Paso 6.4 — Test de Docker

No crear test automatizado, pero documentar en el README el comando para verificar que el build funciona:
```bash
docker compose build
docker compose run dealscout --help
```

---

## FASE 7: Finalizacion

### Paso 7.1 — Actualizar `README.md`

Reescribir el README con:

- Titulo y descripcion corta (1 linea)
- Seccion "Quick Start" con 3 pasos: clonar, configurar .env, correr con Docker
- Seccion "Uso" con ejemplos de CLI (con y sin Docker)
- Seccion "Fuentes de datos" explicando de donde saca la info
- Seccion "Arquitectura" con diagrama ASCII simple del flujo master → subagentes
- Seccion "Desarrollo" con instrucciones para contribuir (instalar deps, correr tests, linting)
- Seccion "Variables de entorno" con tabla de todas las keys necesarias y cuales son opcionales

### Paso 7.2 — Actualizar `CLAUDE.md`

Actualizar con el stack real, estructura de directorios real, y comandos reales:
- `python cli.py "producto"` como comando principal
- `docker compose run dealscout "producto"` como alternativa Docker
- `pytest` para tests
- `ruff check .` para linting
- La estructura de directorios actualizada

### Paso 7.3 — Actualizar `.gitignore`

Agregar entradas que falten:
- `.env` (CRITICO — nunca commitear API keys)
- `__pycache__/`
- `.venv/`
- `*.pyc`
- `.ruff_cache/`
- `output/`

### Paso 7.4 — Smoke test manual

Ejecutar la siguiente secuencia para validar que todo funciona:
1. `pip install -r requirements.txt`
2. `playwright install chromium`
3. `pytest tests/unit/` — todos los tests unitarios deben pasar
4. `python cli.py --help` — debe mostrar la ayuda
5. `python cli.py "audifonos bluetooth"` — debe ejecutar busqueda real (requiere API keys)
6. `ruff check .` — sin errores de linting

---

## Orden de Implementacion Recomendado

```
Fase 0 (Setup)     →  30 min  →  Base del proyecto
Fase 1 (Schemas)   →  45 min  →  Modelos de datos
Fase 2 (Tools)     →  2-3 hrs →  La parte mas compleja, APIs reales
Fase 3 (Utils)     →  30 min  →  Formateo y normalizacion
Fase 4 (Subagentes)→  1 hr    →  Definicion de agentes especializados
Fase 5 (Master+CLI)→  1 hr    →  Orquestacion y entry point
Fase 6 (Docker)    →  30 min  →  Containerizacion
Fase 7 (Finalizac.)→  30 min  →  Documentacion y cleanup
```

**Total estimado: ~6-8 horas de implementacion**

---

## Notas Criticas para el Implementador

1. **Leer `docs/LANGGRAPH_GUIDE.md` ANTES de implementar la Fase 4 y 5.** Contiene la API exacta de `create_deep_agent`, subagentes, y backends.

2. **Leer `docs/WEB_BROWSING_RESEARCH.md` ANTES de implementar la Fase 2.** Contiene detalles de cada API, pricing, y limitaciones.

3. **Precios chilenos:** El punto (.) es separador de miles, NO decimal. $149.990 = ciento cuarenta y nueve mil novecientos noventa pesos. Los precios son siempre enteros.

4. **APIs gratuitas primero:** Solotodo y MercadoLibre son gratis y sin OAuth para busquedas. Implementarlas primero y verificar que funcionan antes de integrar APIs de pago.

5. **Firecrawl es de pago** ($16/mes minimo). El agente debe funcionar de forma degradada sin Firecrawl (usando solo Solotodo + MercadoLibre + SerpAPI).

6. **Playwright en Docker** requiere `--ipc=host` y un usuario no-root. Sin esto, Chromium crashea por falta de shared memory.

7. **Rate limiting:** Respetar limites de las APIs. Agregar delays entre requests a Knasta y sitios de retail. No bombardear Falabella o Ripley con requests rapidos.

8. **Cada tool debe manejar sus propios errores.** Nunca debe explotar una excepcion no manejada desde un tool hacia el agente. Retornar lista vacia o SearchResult con success=False.

9. **Type hints en TODO.** Es una regla del proyecto (ver CLAUDE.md). Cada funcion debe tener tipos en parametros y retorno.

10. **Consultar la documentacion actualizada de cada API antes de implementar.** Los endpoints y estructuras de respuesta descritos en este plan son orientativos. Verificar contra la documentacion oficial:
    - Solotodo: `https://publicapi.solotodo.com/`
    - MercadoLibre: `https://developers.mercadolibre.cl/`
    - SerpAPI: `https://serpapi.com/google-shopping-api`
    - Firecrawl: `https://docs.firecrawl.dev/`
    - DeepAgents: `https://docs.langchain.com/oss/python/deepagents/`
