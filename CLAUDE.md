# DealScout-Agent

## Contexto
Agente autonomo para busqueda y comparacion de ofertas de productos en el mercado chileno.
Construido con DeepAgents SDK (sobre LangGraph/LangChain). Corre en Docker, se ejecuta por CLI.

## Stack
- **Lenguaje:** Python 3.11+
- **Agente:** DeepAgents SDK (`create_deep_agent`) sobre LangGraph
- **LLM:** Claude Sonnet 4.6 (Anthropic)
- **Scraping:** Firecrawl (principal) + Playwright (fallback)
- **APIs:** Solotodo API, MercadoLibre API, SerpAPI Google Shopping
- **CLI:** Typer + Rich
- **Testing:** Pytest + pytest-asyncio
- **Linting:** Ruff
- **Package manager:** uv

## Comandos clave

```bash
# Setup
uv sync                          # Instalar dependencias
uv run playwright install chromium  # Instalar Chromium

# Usar el agente
uv run python cli.py "PlayStation 5"
uv run python cli.py "iPhone 15 128gb" --budget 800000
uv run python cli.py "notebook gamer" --json

# Docker (alternativa)
docker compose run dealscout "PlayStation 5"

# Desarrollo
uv run pytest tests/unit/        # Tests unitarios (sin API keys)
uv run pytest                    # Todos los tests (requiere .env)
uv run ruff check .              # Linting
uv run ruff format .             # Formateo
```

## Estructura del proyecto

```
dealscout-agent/
├── cli.py                   # Entry point CLI (Typer)
├── pyproject.toml           # Dependencias y config (uv)
├── .env.example             # Variables de entorno requeridas
├── Dockerfile               # Imagen Docker con Playwright/Chromium
├── docker-compose.yml
├── src/
│   ├── agent/
│   │   ├── master.py        # create_dealscout_agent() - agente principal
│   │   ├── searcher.py      # Subagente: busqueda en APIs
│   │   ├── scraper.py       # Subagente: extraccion de paginas
│   │   └── comparator.py    # Subagente: analisis y recomendacion
│   ├── tools/
│   │   ├── solotodo.py      # Tool: Solotodo API (electronica CL)
│   │   ├── mercadolibre.py  # Tool: MercadoLibre API
│   │   ├── serpapi_shopping.py  # Tool: Google Shopping Chile
│   │   ├── firecrawl_extract.py # Tool: extraccion web estructurada
│   │   ├── playwright_scraper.py # Tool: navegador headless (fallback)
│   │   └── knasta.py        # Tool: historial de precios (Knasta.cl)
│   ├── schemas/
│   │   ├── product.py       # ProductListing, DealResult, PriceHistory
│   │   └── search.py        # SearchQuery, SearchResult
│   └── utils/
│       ├── price.py         # Normalizacion CLP, calculos de descuento
│       └── output.py        # Formateo Rich para terminal
├── tests/
│   ├── unit/                # Tests sin API keys (rapidos)
│   └── integration/         # Tests con API keys reales (marcados @integration)
└── docs/
    ├── LANGGRAPH_GUIDE.md   # Documentacion DeepAgents/LangGraph
    ├── WEB_BROWSING_RESEARCH.md  # Research APIs y scraping
    └── PROJECT-SPEC.md
```

## Variables de entorno

| Variable | Requerida | Descripcion |
|----------|-----------|-------------|
| `ANTHROPIC_API_KEY` | **Si** | API key de Claude |
| `TAVILY_API_KEY` | Recomendada | Busqueda web (1000 creditos/mes gratis) |
| `SERPAPI_KEY` | Recomendada | Google Shopping Chile (250/mes gratis) |
| `FIRECRAWL_API_KEY` | Recomendada | Extraccion web ($16/mes) |
| `MERCADOLIBRE_ACCESS_TOKEN` | No | OAuth avanzado ML (busquedas basicas no lo requieren) |
| `DEALSCOUT_MODEL` | No | Modelo a usar (default: anthropic:claude-sonnet-4-6) |

## Reglas de codigo

- Python con tipado estricto (Type Hints en todo — parametros y retorno)
- Docstrings en funciones principales (especialmente en @tool — el LLM los lee)
- Tests obligatorios para tools y logica de agente
- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`
- Precios chilenos: siempre `int` en CLP, punto como separador de miles ($149.990)
- Tools nunca lanzan excepciones — manejan errores internamente y retornan lista vacia
