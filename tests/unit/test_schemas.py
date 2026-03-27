"""Tests unitarios para los schemas Pydantic de DealScout."""

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from src.schemas import (
    DealResult,
    PriceHistory,
    PricePoint,
    ProductListing,
    SearchQuery,
    SearchResult,
)

# ─── Helpers ────────────────────────────────────────────────────────────────

def make_listing(**kwargs) -> ProductListing:
    """Crea un ProductListing valido con valores por defecto."""
    defaults = {
        "name": "iPhone 15 128GB",
        "price": 649990,
        "store": "MercadoLibre",
        "url": "https://www.mercadolibre.cl/producto/123",
        "source": "mercadolibre_api",
    }
    defaults.update(kwargs)
    return ProductListing(**defaults)


def make_deal_result(**kwargs) -> DealResult:
    """Crea un DealResult valido con valores por defecto."""
    defaults = {
        "query": "iPhone 15",
        "best_deal": make_listing(),
        "alternatives": [
            make_listing(store="Falabella", price=679990, url="https://falabella.com/p/1", source="firecrawl"),
            make_listing(store="Ripley", price=689990, url="https://ripley.cl/p/2", source="firecrawl"),
            make_listing(store="PCFactory", price=699990, url="https://pcfactory.cl/p/3", source="firecrawl"),
        ],
        "recommendation": "MercadoLibre ofrece el mejor precio con envio gratis.",
        "total_results_found": 15,
        "sources_consulted": ["MercadoLibre API", "Solotodo API", "Falabella via Firecrawl"],
        "search_duration_seconds": 12.5,
    }
    defaults.update(kwargs)
    return DealResult(**defaults)


# ─── ProductListing ──────────────────────────────────────────────────────────

class TestProductListing:
    def test_valid_listing(self):
        listing = make_listing()
        assert listing.name == "iPhone 15 128GB"
        assert listing.price == 649990
        assert listing.currency == "CLP"
        assert listing.in_stock is True
        assert isinstance(listing.scraped_at, datetime)

    def test_rejects_zero_price(self):
        with pytest.raises(ValidationError, match="mayor a 0"):
            make_listing(price=0)

    def test_rejects_negative_price(self):
        with pytest.raises(ValidationError, match="mayor a 0"):
            make_listing(price=-1000)

    def test_rejects_url_without_http(self):
        with pytest.raises(ValidationError, match="http"):
            make_listing(url="www.mercadolibre.cl/producto/123")

    def test_rejects_original_price_less_than_price(self):
        with pytest.raises(ValidationError, match="no puede ser menor"):
            make_listing(price=649990, original_price=600000)

    def test_accepts_original_price_equal_to_price(self):
        # No deberia lanzar error si original == actual
        listing = make_listing(price=649990, original_price=649990)
        assert listing.original_price == 649990

    def test_discount_percentage(self):
        listing = make_listing(price=500000, original_price=700000)
        assert listing.discount_percentage == pytest.approx(28.6, abs=0.1)

    def test_discount_percentage_no_original(self):
        listing = make_listing(price=649990)
        assert listing.discount_percentage is None

    def test_savings_amount(self):
        listing = make_listing(price=500000, original_price=700000)
        assert listing.savings_amount == 200000

    def test_optional_fields_default_none(self):
        listing = make_listing()
        assert listing.original_price is None
        assert listing.shipping_info is None
        assert listing.rating is None
        assert listing.review_count is None
        assert listing.image_url is None

    def test_rating_bounds(self):
        listing = make_listing(rating=4.8)
        assert listing.rating == 4.8

    def test_rejects_rating_out_of_bounds(self):
        with pytest.raises(ValidationError):
            make_listing(rating=5.5)


# ─── PriceHistory ────────────────────────────────────────────────────────────

class TestPriceHistory:
    def test_valid_price_history(self):
        history = PriceHistory(
            product_name="iPhone 15",
            store="Falabella",
            prices=[
                PricePoint(price=700000, recorded_at=date(2026, 1, 1)),
                PricePoint(price=650000, recorded_at=date(2026, 2, 1)),
            ],
            average_price=675000,
            lowest_price=650000,
            highest_price=700000,
        )
        assert history.product_name == "iPhone 15"
        assert len(history.prices) == 2


# ─── DealResult ──────────────────────────────────────────────────────────────

class TestDealResult:
    def test_valid_deal_result(self):
        result = make_deal_result()
        assert result.query == "iPhone 15"
        assert result.total_results_found == 15
        assert len(result.alternatives) == 3
        assert isinstance(result.searched_at, datetime)

    def test_requires_at_least_one_alternative(self):
        with pytest.raises(ValidationError):
            make_deal_result(alternatives=[])

    def test_max_nine_alternatives(self):
        with pytest.raises(ValidationError):
            make_deal_result(alternatives=[
                make_listing(store=f"Tienda{i}", price=649990 + i * 1000,
                             url=f"https://tienda{i}.cl/p/{i}", source="firecrawl")
                for i in range(10)
            ])

    def test_serialization_deserialization(self):
        result = make_deal_result()
        json_str = result.model_dump_json()
        reconstructed = DealResult.model_validate_json(json_str)
        assert reconstructed.query == result.query
        assert reconstructed.best_deal.price == result.best_deal.price
        assert len(reconstructed.alternatives) == len(result.alternatives)


# ─── SearchQuery ─────────────────────────────────────────────────────────────

class TestSearchQuery:
    def test_minimal_query(self):
        query = SearchQuery(product_name="notebook gamer")
        assert query.product_name == "notebook gamer"
        assert query.max_budget is None
        assert query.preferred_stores == []
        assert query.category is None

    def test_full_query(self):
        query = SearchQuery(
            product_name="PS5",
            max_budget=700000,
            preferred_stores=["Falabella", "Ripley"],
            category="videojuegos",
        )
        assert query.max_budget == 700000
        assert "Falabella" in query.preferred_stores


# ─── SearchResult ─────────────────────────────────────────────────────────────

class TestSearchResult:
    def test_successful_result(self):
        result = SearchResult(
            listings=[make_listing()],
            source="solotodo_api",
            raw_query="iphone 15",
            success=True,
        )
        assert result.success is True
        assert result.count == 1
        assert result.error_message is None

    def test_failed_result(self):
        result = SearchResult(
            listings=[],
            source="serpapi",
            raw_query="iphone 15",
            success=False,
            error_message="SERPAPI_KEY no configurada",
        )
        assert result.success is False
        assert result.count == 0
        assert "SERPAPI_KEY" in result.error_message
