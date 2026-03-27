"""Schemas Pydantic para productos y resultados del agente DealScout."""

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, Field, model_validator


class PricePoint(BaseModel):
    """Un punto de precio en el tiempo."""

    price: int = Field(gt=0, description="Precio en CLP")
    recorded_at: date = Field(description="Fecha del registro de precio")


class PriceHistory(BaseModel):
    """Historial de precios de un producto en una tienda."""

    product_name: str = Field(description="Nombre del producto")
    store: str = Field(description="Nombre de la tienda")
    prices: list[PricePoint] = Field(default_factory=list, description="Lista de puntos de precio historicos")
    average_price: int = Field(gt=0, description="Precio promedio historico en CLP")
    lowest_price: int = Field(gt=0, description="Precio mas bajo historico en CLP")
    highest_price: int = Field(gt=0, description="Precio mas alto historico en CLP")


class ProductListing(BaseModel):
    """Representa un producto encontrado en una tienda chilena."""

    name: str = Field(description="Nombre del producto tal como aparece en la tienda")
    price: int = Field(description="Precio actual en CLP (pesos chilenos, entero sin decimales)")
    currency: str = Field(default="CLP", description="Moneda, siempre CLP para mercado chileno")
    store: str = Field(description="Nombre de la tienda (ej: Falabella, MercadoLibre, PCFactory)")
    url: str = Field(description="URL directa al producto en la tienda")
    in_stock: bool = Field(default=True, description="Si el producto esta disponible para compra")
    original_price: int | None = Field(
        default=None,
        description="Precio original antes de descuento, None si no hay oferta",
    )
    shipping_info: str | None = Field(
        default=None,
        description="Informacion de envio (ej: 'Envio gratis', 'Despacho en 3-5 dias')",
    )
    rating: float | None = Field(
        default=None,
        ge=0.0,
        le=5.0,
        description="Rating del producto de 0.0 a 5.0",
    )
    review_count: int | None = Field(
        default=None,
        ge=0,
        description="Cantidad de reviews del producto",
    )
    image_url: str | None = Field(default=None, description="URL de la imagen del producto")
    source: str = Field(
        description="Origen del dato: solotodo_api | mercadolibre_api | serpapi | firecrawl | playwright",
    )
    scraped_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp de cuando se obtuvo el dato",
    )

    @model_validator(mode="after")
    def validate_product(self) -> "ProductListing":
        """Valida coherencia interna del producto."""
        if self.price <= 0:
            raise ValueError(f"El precio debe ser mayor a 0, recibido: {self.price}")
        if not self.url.startswith("http"):
            raise ValueError(f"La URL debe comenzar con 'http', recibida: {self.url}")
        if self.original_price is not None and self.original_price < self.price:
            raise ValueError(
                f"El precio original ({self.original_price}) no puede ser menor al precio actual ({self.price})"
            )
        # Rechazar URLs de paginas de busqueda — deben ser URLs directas a un producto.
        # Patrones comunes de hallucination: /search?q=, /buscar?, etc.
        _SEARCH_PATTERNS = ("/search?", "/buscar?", "/resultados?", "/categoria?", "?query=", "?keyword=")
        for pattern in _SEARCH_PATTERNS:
            if pattern in self.url:
                raise ValueError(
                    f"La URL parece ser una pagina de busqueda, no un producto directo: {self.url}. "
                    "Usa solo URLs directas al producto retornadas por las herramientas."
                )
        return self

    @property
    def discount_percentage(self) -> float | None:
        """Calcula el porcentaje de descuento si hay precio original."""
        if self.original_price and self.original_price > self.price:
            return round((1 - self.price / self.original_price) * 100, 1)
        return None

    @property
    def savings_amount(self) -> int | None:
        """Cuanto se ahorra respecto al precio original."""
        if self.original_price and self.original_price > self.price:
            return self.original_price - self.price
        return None


class DealResult(BaseModel):
    """Resultado final del agente DealScout con la mejor opcion y alternativas."""

    query: str = Field(description="Busqueda original del usuario")
    best_deal: ProductListing = Field(description="La mejor opcion recomendada")
    alternatives: Annotated[list[ProductListing], Field(min_length=1, max_length=5)] = Field(
        description="Alternativas ordenadas de mejor a peor (minimo 1, maximo 5)"
    )
    price_history: PriceHistory | None = Field(
        default=None,
        description="Historial de precios si se pudo obtener de Knasta",
    )
    recommendation: str = Field(
        description="Explicacion en 2-3 oraciones de por que esa es la mejor opcion"
    )
    total_results_found: int = Field(
        ge=0,
        description="Total de resultados encontrados antes de filtrar y rankear",
    )
    sources_consulted: list[str] = Field(
        description="Lista de fuentes consultadas (ej: ['Solotodo API', 'MercadoLibre API'])"
    )
    search_duration_seconds: float = Field(
        ge=0.0,
        description="Duracion total de la busqueda en segundos",
    )
    searched_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp de cuando se realizo la busqueda",
    )
