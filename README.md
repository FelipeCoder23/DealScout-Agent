# DealScout Agent

Agente autonomo que busca y compara precios de productos en el mercado chileno.
Consulta Solotodo, MercadoLibre, Google Shopping Chile y tiendas como Falabella y Ripley
para encontrar la mejor oferta con links directos.

## Quick Start (Docker)

```bash
# 1. Clonar el repositorio
git clone https://github.com/FelipeCoder23/DealScout-Agent.git
cd DealScout-Agent

# 2. Configurar API keys
cp .env.example .env
# Editar .env y agregar al menos ANTHROPIC_API_KEY

# 3. Buscar un producto
docker compose run --rm dealscout "PlayStation 5"
```

## Quick Start (Local con uv)

```bash
# Instalar dependencias
uv sync

# Instalar navegador Chromium (para scraping avanzado)
uv run playwright install chromium

# Configurar API keys
cp .env.example .env
# Editar .env

# Buscar un producto
uv run python cli.py "iPhone 15 128gb"
```

## Uso

```bash
# Busqueda basica
dealscout "PlayStation 5"
uv run python cli.py "PlayStation 5"

# Con presupuesto maximo en CLP
dealscout "iPhone 15 128gb" --budget 800000
uv run python cli.py "iPhone 15 128gb" -b 800000

# Output en JSON (para integracion con otros sistemas)
dealscout "notebook gamer" --json

# Con informacion de progreso
dealscout "audifonos bluetooth" --verbose
```

## Ejemplo de Output

```
╭─────────────── 🏆 MEJOR OPCION ───────────────╮
│ iPhone 15 128GB - Negro                        │
│ $649.990 en MercadoLibre (VendedorTop)         │
│ Precio original: $699.990 (-7.2% — ahorras     │
│ $50.000)                                       │
│ Envio gratis                                   │
│ ★★★★★ 4.8/5.0                                  │
│ https://mercadolibre.cl/p/MLC123456789         │
╰────────────────────────────────────────────────╯

El mejor precio esta en MercadoLibre a $649.990,
unos $50.000 menos que Falabella. El vendedor
tiene 98% reputacion positiva y envio gratis.

📊 ALTERNATIVAS
┌───┬──────────┬───────────┬───────────┬──────────────┐
│ # │ Tienda   │ Precio    │ Diferencia│ Envio        │
├───┼──────────┼───────────┼───────────┼──────────────┤
│ 1 │ Falabella│ $699.990  │ +$50.000  │ No informado │
│ 2 │ Ripley   │ $719.990  │ +$70.000  │ No informado │
│ 3 │ PCFactory│ $679.990  │ +$30.000  │ Envio gratis │
└───┴──────────┴───────────┴───────────┴──────────────┘
```

## Arquitectura

```
CLI (cli.py)
    └── Master Agent (DeepAgent SDK)
            ├── searcher-agent    → Solotodo API + MercadoLibre API + Google Shopping CL
            ├── scraper-agent     → Firecrawl + Playwright fallback
            └── comparator-agent → Analisis + Historial de precios (Knasta)
```

## Fuentes de Datos

| Fuente | Tipo | Cobertura | Costo |
|--------|------|-----------|-------|
| Solotodo API | API publica | Electronica y tecnologia | Gratis |
| MercadoLibre API | API publica | Todo tipo de productos | Gratis |
| SerpAPI Google Shopping | API | Multiples tiendas CL | 250/mes gratis |
| Firecrawl | Extraccion web | Cualquier tienda | $16/mes |
| Playwright | Navegador | Fallback para sitios bloqueados | Gratis |
| Knasta | Scraping | Historial de precios | Gratis |

## Variables de Entorno

| Variable | Requerida | Descripcion |
|----------|-----------|-------------|
| `ANTHROPIC_API_KEY` | **Si** | API key de Claude (Anthropic) |
| `TAVILY_API_KEY` | Recomendada | Busqueda web (1000/mes gratis) |
| `SERPAPI_KEY` | Recomendada | Google Shopping Chile (250/mes gratis) |
| `FIRECRAWL_API_KEY` | Recomendada | Extraccion web ($16/mes) |
| `MERCADOLIBRE_ACCESS_TOKEN` | No | OAuth avanzado ML |
| `DEALSCOUT_MODEL` | No | Modelo LLM (default: claude-sonnet-4-6) |

## Desarrollo

```bash
# Instalar dependencias (incluyendo dev)
uv sync --dev

# Correr tests unitarios (sin API keys)
uv run pytest tests/unit/ -v

# Correr todos los tests (requiere .env con API keys)
uv run pytest -v

# Solo tests de integracion
uv run pytest -m integration -v

# Linting
uv run ruff check .

# Formateo
uv run ruff format .

# Build Docker
docker compose build

# Verificar imagen
docker compose run --rm dealscout --help
```
