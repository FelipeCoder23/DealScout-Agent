"""Schemas Pydantic para queries y resultados intermedios de busqueda."""

from pydantic import BaseModel, Field

from src.schemas.product import ProductListing


class SearchQuery(BaseModel):
    """Representa la busqueda que solicita el usuario."""

    product_name: str = Field(description="Nombre del producto a buscar")
    max_budget: int | None = Field(
        default=None,
        gt=0,
        description="Presupuesto maximo en CLP. None significa sin limite.",
    )
    preferred_stores: list[str] = Field(
        default_factory=list,
        description="Tiendas preferidas. Lista vacia significa buscar en todas.",
    )
    category: str | None = Field(
        default=None,
        description="Categoria del producto (ej: 'electronica', 'hogar', 'deportes')",
    )


class SearchResult(BaseModel):
    """Resultado intermedio de una tool de busqueda."""

    listings: list[ProductListing] = Field(
        default_factory=list,
        description="Productos encontrados por esta fuente",
    )
    source: str = Field(description="Nombre de la tool/fuente que genero este resultado")
    raw_query: str = Field(description="Query exacto que se uso para buscar")
    success: bool = Field(description="Si la busqueda fue exitosa")
    error_message: str | None = Field(
        default=None,
        description="Mensaje de error si success=False",
    )

    @property
    def count(self) -> int:
        """Cantidad de listings encontrados."""
        return len(self.listings)
