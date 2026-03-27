"""Master Agent de DealScout — orquesta la busqueda y comparacion de productos."""

import os
import time

from deepagents import create_deep_agent

from src.agent.comparator import create_comparator_subagent
from src.agent.scraper import create_scraper_subagent
from src.agent.searcher import create_searcher_subagent
from src.schemas.product import DealResult
from src.tools.mercadolibre import search_mercadolibre
from src.tools.solotodo import search_solotodo

_MASTER_SYSTEM_PROMPT = """Eres DealScout, el mejor experto en encontrar ofertas de productos en el mercado chileno.

Tu mision: dado el nombre de un producto, encontrar la MEJOR opcion de compra y 3 alternativas con links directos.

FLUJO DE TRABAJO:
1. BUSQUEDA INICIAL — Delega al searcher-agent:
   - Le pasas el nombre del producto
   - El buscara en Solotodo, MercadoLibre y Google Shopping Chile
   - Recibiras una lista de productos con precios y URLs

2. EXTRACCION ADICIONAL (si es necesario) — Delega al scraper-agent:
   - Si el searcher encontro URLs de Falabella, Ripley o Paris sin precios completos
   - Le pasas esas URLs para que extraiga los datos detallados
   - Si ya tienes suficientes resultados con precios completos, puedes omitir este paso

3. ANALISIS Y RECOMENDACION — Delega al comparator-agent:
   - Le pasas la lista consolidada de todos los productos encontrados
   - El analizara precio, confiabilidad, envio y rating
   - Retornara la mejor opcion y 3 alternativas con justificacion

4. PRESENTA EL RESULTADO FINAL al usuario con:
   - Mejor opcion: nombre, precio, tienda, URL
   - 3 alternativas con sus precios y URLs
   - Recomendacion explicando el por que

REGLAS CRITICAS:
- Todos los precios son en pesos chilenos (CLP), enteros, sin decimales
- El punto (.) es separador de miles en Chile: $149.990 = ciento cuarenta y nueve mil novecientos noventa
- Las URLs de los productos DEBEN venir EXACTAMENTE de las herramientas — NUNCA inventar ni construir URLs
- Una URL valida es la que retorno una tool: permalink de MercadoLibre, URL de Solotodo, etc.
- JAMAS usar URLs de paginas de busqueda como /search?q=... — el sistema las rechazara con error
- Si no tienes URL directa de un producto, NO incluirlo en el resultado
- Minimo debes consultar 2 fuentes diferentes antes de dar una recomendacion
- Si un subagente falla, continuar con los datos parciales disponibles
- El resultado DEBE tener: mejor opcion + al menos 1 alternativa

CONTEXTO DEL MERCADO CHILENO:
- Tiendas grandes confiables: Falabella, Ripley, Paris, PCFactory, SP Digital, Sodimac
- Marketplaces: MercadoLibre (el mas grande), Yapo (articulos usados)
- Comparadores: Solotodo (electronica), Knasta (historial de precios)
- Eventos especiales: CyberDay y CyberMonday (precios mas bajos del año)
- Los precios en Chile incluyen IVA (19%) — no hay que sumar impuestos

Si el usuario especifica un presupuesto maximo, solo recomendar opciones dentro de ese rango.
Si el usuario no especifica categoria, inferirla del nombre del producto.
"""


def create_dealscout_agent():
    """Crea y retorna el agente principal de DealScout configurado con todos los subagentes.

    Returns:
        Agente DeepAgent listo para invocar con .invoke()
    """
    model = os.environ.get("DEALSCOUT_MODEL", "anthropic:claude-sonnet-4-6")

    return create_deep_agent(
        name="dealscout",
        model=model,
        tools=[
            # Tools directas en el master como fallback rapido
            search_solotodo,
            search_mercadolibre,
        ],
        subagents=[
            create_searcher_subagent(),
            create_scraper_subagent(),
            create_comparator_subagent(),
        ],
        system_prompt=_MASTER_SYSTEM_PROMPT,
        response_format=DealResult,
    )


def run_search(query: str, max_budget: int | None = None) -> DealResult:
    """Ejecuta una busqueda de producto y retorna el mejor deal encontrado.

    Args:
        query: Nombre del producto a buscar (ej: 'iPhone 15 128GB', 'PS5')
        max_budget: Presupuesto maximo en CLP (opcional)

    Returns:
        DealResult con la mejor opcion, alternativas y recomendacion.

    Raises:
        ValueError: Si no se puede crear el agente (falta ANTHROPIC_API_KEY)
        RuntimeError: Si el agente no puede completar la busqueda
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise ValueError(
            "ANTHROPIC_API_KEY no configurada. "
            "Configura tu API key de Anthropic en el archivo .env"
        )

    start_time = time.time()

    # Construir el mensaje del usuario
    if max_budget:
        from src.utils.price import format_clp
        budget_str = format_clp(max_budget)
        user_message = (
            f"Busca el mejor precio para: {query}\n"
            f"Presupuesto maximo: {budget_str} CLP"
        )
    else:
        user_message = f"Busca el mejor precio para: {query}"

    agent = create_dealscout_agent()

    result = agent.invoke({
        "messages": [{"role": "user", "content": user_message}]
    })

    # Extraer el DealResult del resultado del agente
    structured = result.get("structured_response")

    if isinstance(structured, DealResult):
        # Actualizar duracion real de la busqueda
        duration = time.time() - start_time
        # Pydantic v2: crear nueva instancia con duracion actualizada
        return structured.model_copy(update={"search_duration_seconds": round(duration, 2)})

    # Si el agente no pudo generar un DealResult estructurado, intentar parsear
    # el ultimo mensaje como fallback
    raise RuntimeError(
        "El agente no pudo generar una recomendacion estructurada. "
        "Verifica que las API keys esten configuradas correctamente."
    )
