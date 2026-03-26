# DealScout-Agent

## Contexto
Agente autónomo para búsqueda y comparación de ofertas de productos específicos en tiempo real.

## Stack
- **Lenguaje:** Python 3.11+
- **Backend/API:** FastAPI
- **Scraping:** Playwright / BeautifulSoup
- **Orquestación:** LangGraph / LangChain
- **Testing:** Pytest
- **Linting:** Ruff / Black

## Comandos clave

```bash
python -m venv .venv        # Crear entorno virtual
source .venv/bin/activate   # Activar entorno (Linux/macOS)
pip install -r requirements.txt # Instalar dependencias
pytest                      # Correr tests
ruff check .                # Verificar linting
```

## Estructura del proyecto

```
src/
├── agent/          # Lógica del agente (LangGraph)
├── scrapers/       # Módulos de scraping por sitio
├── schemas/        # Modelos Pydantic
├── utils/          # Helpers
└── tests/          # Tests unitarios e integración
docs/
├── PROJECT-SPEC.md # Especificación del proyecto
└── API.md          # Documentación de la API (si aplica)
```

## Reglas de código

- Python con tipado estricto (Type Hints)
- Tests obligatorios para scrapers y lógica de agente
- Conventional commits (feat:, fix:, refactor:)
- Docstrings en funciones principales

## Variables de entorno

```env
# [Agregar API keys de ser necesario, e.g., OpenAI/Anthropic para el agente]
ANTHROPIC_API_KEY=
```
