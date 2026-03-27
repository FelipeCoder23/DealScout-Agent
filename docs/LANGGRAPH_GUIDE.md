# DeepAgents + LangGraph - Guía Completa

**Fuentes:**
- `https://docs.langchain.com/oss/python/deepagents/overview`
- `https://docs.langchain.com/oss/python/deepagents/quickstart`
- `https://docs.langchain.com/oss/python/deepagents/customization`
- `https://docs.langchain.com/oss/python/deepagents/subagents`
- `https://docs.langchain.com/oss/python/deepagents/backends`

---

## Tabla de Contenidos
1. [¿Qué es DeepAgents?](#qué-es-deepagents)
2. [Instalación y Setup](#instalación-y-setup)
3. [create_deep_agent — Parámetros](#create_deep_agent--parámetros)
4. [Herramientas Personalizadas](#herramientas-personalizadas)
5. [Subagentes](#subagentes)
6. [Backends (Filesystem)](#backends-filesystem)
7. [Middleware Integrado](#middleware-integrado)
8. [Memoria Persistente y Skills](#memoria-persistente-y-skills)
9. [Human-in-the-Loop](#human-in-the-loop)
10. [Salida Estructurada](#salida-estructurada)
11. [LangGraph (Runtime Base)](#langgraph-runtime-base)

---

## ¿Qué es DeepAgents?

**DeepAgents** es un "agent harness" construido sobre LangChain, con LangGraph como runtime para ejecución durable y streaming. Incluye:

- **SDK de DeepAgents** — Para construir agentes complejos y autónomos
- **CLI de DeepAgents** — Agente de codificación terminal basado en el SDK

### Capacidades centrales

| Capacidad | Descripción |
|-----------|-------------|
| **Planificación** | Tool `write_todos` — descompone tareas complejas en pasos discretos |
| **Gestión de contexto** | Filesystem virtual (`ls`, `read_file`, `write_file`, `edit_file`) para offload de contexto |
| **Backends pluggables** | Filesystem intercambiable: memoria, disco, LangGraph store, sandboxes |
| **Subagentes** | Tool `task` integrada para spawning de agentes especializados con contexto aislado |
| **Memoria persistente** | Integración con Memory Store de LangGraph entre conversaciones |
| **Resiliencia** | Retry automático con exponential backoff (hasta 6 veces por defecto, configurable a 10-15) |

---

## Instalación y Setup

```bash
# Instalar
pip install deepagents tavily-python
# o con uv
uv init && uv add deepagents tavily-python && uv sync
```

### Variables de entorno por proveedor

```bash
# Anthropic (recomendado para DealScout)
ANTHROPIC_API_KEY=...
TAVILY_API_KEY=...

# OpenAI
OPENAI_API_KEY=...
TAVILY_API_KEY=...

# Google
GOOGLE_API_KEY=...
TAVILY_API_KEY=...
```

---

## `create_deep_agent` — Parámetros

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    name="deal-scout",                  # Opcional: identificador del agente
    model="anthropic:claude-sonnet-4-6",# Proveedor:modelo (default: claude-sonnet-4-6)
    tools=[...],                        # Funciones/callables personalizados
    system_prompt="...",                # Instrucciones del sistema
    middleware=[...],                   # Extensiones de funcionalidad
    subagents=[...],                    # Agentes especializados para delegar
    backend=...,                        # Sistema de archivos virtual
    memory=...,                         # Contexto persistente entre sesiones
    skills=[...],                       # Capacidades especializadas (archivos SKILL.md)
    response_format=MyPydanticModel,    # Salida estructurada
)
```

### Modelos soportados

```python
# Anthropic
model = "claude-sonnet-4-6"               # Default
model = "anthropic:claude-sonnet-4-6"

# OpenAI
model = "openai:gpt-5.2"

# Google
model = "google_genai:gemini-2.5-flash-lite"

# AWS Bedrock
model = "anthropic.claude-3-5-sonnet-20240620-v1:0"

# Azure
model = "azure_openai:gpt-5.2"
```

### Uso básico

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    tools=[my_tool],
    system_prompt="Eres un agente especializado en buscar deals."
)

# Invocar
result = agent.invoke({"messages": [{"role": "user", "content": "Busca ofertas de laptops"}]})
print(result["messages"][-1].content)
```

---

## Herramientas Personalizadas

```python
from langchain.tools import tool
from typing import Literal

@tool
def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False
) -> list:
    """Busca información en internet usando Tavily."""
    from tavily import TavilyClient
    client = TavilyClient()
    return client.search(query, max_results=max_results)

@tool
def scrape_price(url: str) -> dict:
    """Extrae el precio de un producto en una URL dada."""
    # Tu lógica de scraping aquí
    ...
```

**Regla clave:** El docstring es la descripción que ve el LLM. Sé específico y claro.

---

## Subagentes

### Cuándo usarlos

**Usar subagentes cuando:**
- Tareas multi-paso que saturarían el contexto principal
- Dominios especializados con instrucciones propias
- Tareas que requieren un modelo diferente

**No usar cuando:**
- La tarea es simple y de un solo paso
- Necesitas mantener contexto intermedio compartido

### Enfoque 1: Diccionario (recomendado)

```python
research_subagent = {
    "name": "research-agent",
    "description": "Investiga precios y ofertas en profundidad",  # CLAVE: define cuándo delegar
    "system_prompt": "Eres un experto en investigación de precios. Devuelve información concisa.",
    "tools": [internet_search, scrape_url],
    "model": "openai:gpt-5.2"  # Opcional, hereda del agente principal si se omite
}

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    subagents=[research_subagent, compare_subagent]
)
```

**Campos requeridos:**
- `name` — Identificador único (snake-case recomendado)
- `description` — Determina cuándo el agente principal le delega trabajo
- `system_prompt` — Instrucciones específicas del subagente
- `tools` — Solo las herramientas necesarias para su dominio

### Enfoque 2: CompiledSubAgent (LangGraph avanzado)

```python
from deepagents import CompiledSubAgent

# custom_graph = un grafo LangGraph compilado
custom_subagent = CompiledSubAgent(
    name="data-analyzer",
    description="Analiza datos complejos con lógica de grafo personalizada",
    runnable=custom_graph  # Grafo LangGraph compilado
)

agent = create_deep_agent(subagents=[custom_subagent])
```

### Ejemplo: Multi-subagent para DealScout

```python
scraper_agent = {
    "name": "scraper-agent",
    "description": "Extrae precios y datos de productos de sitios web específicos",
    "system_prompt": "Eres experto en web scraping. Extrae precio, nombre, disponibilidad y URL. Devuelve JSON.",
    "tools": [scrape_page, extract_price],
}

comparator_agent = {
    "name": "comparator-agent",
    "description": "Compara precios entre múltiples productos y determina el mejor deal",
    "system_prompt": "Analiza precios, calidad/precio y reputación del vendedor. Rankea de mejor a peor.",
    "tools": [calculate_score, fetch_reviews],
}

master_agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    tools=[internet_search],
    subagents=[scraper_agent, comparator_agent],
    system_prompt="Coordinas la búsqueda y comparación de deals. Delega scraping y comparación a tus subagentes."
)
```

### Contexto por subagente

```python
# El contexto general se propaga a todos los subagentes
# Para contexto específico por subagente, usa prefijo:
result = await agent.invoke(
    {"messages": [{"role": "user", "content": "..."}]},
    {
        "context": {
            "user_id": "123",                      # Compartido con todos
            "researcher:max_depth": 3,             # Solo para el subagente "researcher"
            "scraper:timeout": 30                  # Solo para el subagente "scraper"
        }
    }
)
```

### Mejores prácticas para subagentes

- **Descripciones claras:** "Analiza datos financieros y genera insights" > "Hace cosas de finanzas"
- **System prompts detallados:** Especifica formato de salida y cómo usar las herramientas
- **Mínimo de tools:** Solo las necesarias → mejor seguridad y menos confusión
- **Resultados concisos:** Instruye devolver resúmenes, no datos crudos

---

## Backends (Filesystem)

El backend determina dónde el agente almacena archivos temporales y de contexto.

### StateBackend (default, efímero)

Almacena en el estado de LangGraph del thread actual. Se pierde al terminar.

```python
from deepagents.backends import StateBackend

agent = create_deep_agent()  # StateBackend por defecto
# o explícito:
agent = create_deep_agent(backend=lambda rt: StateBackend(rt))
```

### FilesystemBackend (disco local)

```python
from deepagents.backends import FilesystemBackend

agent = create_deep_agent(
    backend=FilesystemBackend(root_dir=".", virtual_mode=True)
    # virtual_mode=True restringe acceso fuera del root_dir
)
```

> ⚠️ **Seguridad:** Los agentes pueden leer archivos del directorio. Usar solo en dev o CI/CD controlados.

### LocalShellBackend (shell sin aislamiento)

```python
from deepagents.backends import LocalShellBackend

agent = create_deep_agent(
    backend=LocalShellBackend(root_dir=".", env={"PATH": "/usr/bin:/bin"})
)
```

> ⚠️ **Peligroso:** Ejecuta comandos con permisos del usuario. Solo en desarrollo personal de confianza.

### StoreBackend (cross-thread, persistente)

Persiste entre diferentes ejecuciones/threads. Ideal para memoria a largo plazo.

```python
from deepagents.backends import StoreBackend

agent = create_deep_agent(backend=lambda rt: StoreBackend(rt))
```

### CompositeBackend (rutas múltiples)

Enruta operaciones a diferentes backends según el path. Prefijos más largos tienen prioridad.

```python
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

composite = lambda rt: CompositeBackend(
    default=StateBackend(rt),        # Default para todo
    routes={
        "/memories/": StoreBackend(rt)  # /memories/ persiste entre threads
    }
)

agent = create_deep_agent(backend=composite)
```

### Backend personalizado (S3, Postgres, etc.)

Implementar `BackendProtocol` con estos métodos:

```python
class MyS3Backend:
    def ls_info(self, path): ...
    def read(self, file_path, offset, limit): ...
    def grep_raw(self, pattern, path, glob): ...
    def glob_info(self, pattern, path): ...
    def write(self, file_path, content): ...
    def edit(self, file_path, old_string, new_string): ...
```

### Herramientas de filesystem disponibles para el agente

`ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`, `execute` (solo en Sandboxes/LocalShellBackend)

---

## Middleware Integrado

DeepAgents incluye middleware automático. Los principales:

| Middleware | Función |
|-----------|---------|
| `TodoListMiddleware` | Gestión de listas de tareas (`write_todos`) |
| `FilesystemMiddleware` | Operaciones de archivos virtuales |
| `SubAgentMiddleware` | Coordinación de subagentes (`task` tool) |
| `SummarizationMiddleware` | Compresión de contexto cuando es muy largo |
| `AnthropicPromptCachingMiddleware` | Optimización de tokens con Anthropic |
| `MemoryMiddleware` | Persistencia entre sesiones (`AGENTS.md`) |
| `SkillsMiddleware` | Carga de habilidades especializadas (`SKILL.md`) |

---

## Memoria Persistente y Skills

### Memory (AGENTS.md)

El agente escribe y lee de un archivo `AGENTS.md` para persistir contexto entre sesiones.

```python
agent = create_deep_agent(
    memory=True,  # Habilita MemoryMiddleware con AGENTS.md
    # o con backend específico:
    memory=StoreBackend(rt)
)
```

### Skills (SKILL.md)

Archivos markdown con instrucciones detalladas que el agente carga bajo demanda.

```python
agent = create_deep_agent(
    skills=["./skills/scraping.md", "./skills/pricing.md"]
)
```

---

## Human-in-the-Loop

Requiere aprobación humana para operaciones sensibles. **Requiere checkpointer obligatoriamente.**

```python
from langgraph.checkpoint.memory import MemorySaver

agent = create_deep_agent(
    tools=[send_email, delete_file, purchase_item],
    interrupt_on={
        "delete_file": True,                                      # Interrumpe siempre
        "send_email": {"allowed_decisions": ["approve", "reject"]},  # Con opciones
        "purchase_item": {"allowed_decisions": ["approve", "reject", "modify"]}
    },
    checkpointer=MemorySaver()  # Requerido para HITL
)
```

---

## Salida Estructurada

```python
from pydantic import BaseModel, Field
from typing import List

class DealResult(BaseModel):
    product_name: str = Field(description="Nombre del producto")
    best_price: float = Field(description="Mejor precio encontrado")
    best_url: str = Field(description="URL del mejor deal")
    alternatives: List[dict] = Field(description="Otras opciones encontradas")
    recommendation: str = Field(description="Recomendación final")

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    tools=[internet_search, scrape_price],
    response_format=DealResult
)

result = agent.invoke({"messages": [{"role": "user", "content": "Busca el mejor precio de iPhone 15"}]})
deal: DealResult = result["structured_response"]
print(f"Mejor precio: ${deal.best_price} en {deal.best_url}")
```

---

## LangGraph (Runtime Base)

DeepAgents usa LangGraph internamente. Útil saber para debugging y extender con `CompiledSubAgent`.

### State + Graph básico

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing import Annotated
from typing_extensions import TypedDict

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

def llm_node(state: AgentState):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

def tool_node(state: AgentState):
    # Ejecutar tool calls del último mensaje
    ...

def should_continue(state: AgentState):
    return "tool_node" if state["messages"][-1].tool_calls else END

builder = StateGraph(AgentState)
builder.add_node("llm", llm_node)
builder.add_node("tools", tool_node)
builder.add_edge(START, "llm")
builder.add_conditional_edges("llm", should_continue, ["tools", END])
builder.add_edge("tools", "llm")

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)
```

### Conversaciones multi-turn con thread_id

```python
from langchain_core.runnables import RunnableConfig

config = RunnableConfig(configurable={"thread_id": "session_1"})

# Turn 1
graph.invoke({"messages": [{"role": "user", "content": "Soy Felipe"}]}, config)

# Turn 2 — recuerda el contexto anterior
graph.invoke({"messages": [{"role": "user", "content": "¿Cómo me llamo?"}]}, config)
# → Responde: "Te llamas Felipe"
```

### Reducers de estado

| Reducer | Comportamiento | Uso |
|---------|----------------|-----|
| `add_messages` | Merge/update, deduplica por ID | Message lists |
| `operator.add` | Append (solo agrega, nunca reemplaza) | Historial, logs |
| Default (assign) | Reemplaza el valor | Scalars, flags |

---

## Arquitectura Recomendada para DealScout-Agent

```
create_deep_agent (Master)
├── tools: [internet_search]
├── subagents:
│   ├── scraper-agent        → tools: [scrape_page, extract_data]
│   └── comparator-agent     → tools: [rank_deals, score_price]
├── backend: CompositeBackend
│   ├── default: StateBackend (scratchpad temporal)
│   └── /memories/: StoreBackend (deals históricos)
├── response_format: DealResult (Pydantic)
└── checkpointer: InMemorySaver (para HITL o multi-turn)
```

**Flujo:**
1. Usuario pide "el mejor deal de X"
2. Master agent planifica con `write_todos`
3. Delega scraping al `scraper-agent` via `task` tool
4. Delega comparación al `comparator-agent`
5. Sintetiza y devuelve `DealResult` estructurado
