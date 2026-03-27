"""Schemas Pydantic del agente DealScout."""

from src.schemas.product import DealResult, PriceHistory, PricePoint, ProductListing
from src.schemas.search import SearchQuery, SearchResult

__all__ = [
    "ProductListing",
    "PricePoint",
    "PriceHistory",
    "DealResult",
    "SearchQuery",
    "SearchResult",
]
