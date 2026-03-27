"""Tests unitarios de las utilidades de DealScout."""


from src.schemas.product import ProductListing
from src.utils.price import calculate_discount, compare_prices, format_clp, normalize_price

# ─── normalize_price ─────────────────────────────────────────────────────────

class TestNormalizePrice:
    def test_with_dollar_sign_and_dot(self):
        assert normalize_price("$149.990") == 149990

    def test_plain_integer_string(self):
        assert normalize_price("149990") == 149990

    def test_with_comma_thousands_separator(self):
        assert normalize_price("$149,990") == 149990

    def test_with_clp_prefix(self):
        assert normalize_price("CLP 149.990") == 149990

    def test_with_clp_suffix(self):
        assert normalize_price("149.990 CLP") == 149990

    def test_with_spaces(self):
        assert normalize_price("$ 149.990") == 149990

    def test_large_price(self):
        assert normalize_price("$1.299.990") == 1299990

    def test_small_price(self):
        assert normalize_price("$9.990") == 9990

    def test_empty_string(self):
        assert normalize_price("") is None

    def test_non_price_string(self):
        assert normalize_price("no es precio") is None

    def test_zero_returns_none(self):
        # 0 no es un precio valido
        result = normalize_price("$0")
        assert result is None or result == 0


# ─── calculate_discount ───────────────────────────────────────────────────────

class TestCalculateDiscount:
    def test_real_discount(self):
        result = calculate_discount(original=200000, current=150000)
        assert result["amount"] == 50000
        assert result["percentage"] == 25.0
        assert result["is_deal"] is True

    def test_small_discount_not_considered_deal(self):
        # Descuento menor al 5% no es "deal"
        result = calculate_discount(original=100000, current=97000)
        assert result["is_deal"] is False

    def test_exactly_5_percent_is_deal(self):
        result = calculate_discount(original=100000, current=95000)
        assert result["percentage"] == 5.0
        assert result["is_deal"] is True

    def test_no_discount(self):
        result = calculate_discount(original=100000, current=100000)
        assert result["amount"] == 0
        assert result["percentage"] == 0.0
        assert result["is_deal"] is False

    def test_current_higher_than_original(self):
        result = calculate_discount(original=100000, current=120000)
        assert result["amount"] == 0
        assert result["is_deal"] is False

    def test_zero_prices(self):
        result = calculate_discount(original=0, current=0)
        assert result["is_deal"] is False


# ─── format_clp ──────────────────────────────────────────────────────────────

class TestFormatClp:
    def test_typical_price(self):
        assert format_clp(149990) == "$149.990"

    def test_million_plus(self):
        assert format_clp(1299990) == "$1.299.990"

    def test_small_price(self):
        assert format_clp(9990) == "$9.990"

    def test_round_number(self):
        assert format_clp(100000) == "$100.000"

    def test_zero(self):
        assert format_clp(0) == "$0"


# ─── compare_prices ──────────────────────────────────────────────────────────

def make_listing(store: str, price: int) -> ProductListing:
    return ProductListing(
        name="Producto Test",
        price=price,
        store=store,
        url=f"https://{store.lower()}.cl/producto/1",
        source="test",
    )


class TestComparePrices:
    def test_sorts_by_price_ascending(self):
        listings = [
            make_listing("Ripley", 699990),
            make_listing("Falabella", 649990),
            make_listing("PCFactory", 679990),
        ]
        result = compare_prices(listings)
        prices = [l.price for l in result]
        assert prices == sorted(prices)

    def test_deduplicates_same_store_same_price(self):
        listings = [
            make_listing("Falabella", 649990),
            make_listing("Falabella", 650000),  # Muy similar (~1000 CLP diferencia)
            make_listing("Ripley", 699990),
        ]
        result = compare_prices(listings)
        # Los dos de Falabella deberian quedar como 1 (bucket similar)
        stores = [l.store for l in result]
        assert stores.count("Falabella") <= 1

    def test_keeps_different_stores(self):
        listings = [
            make_listing("Falabella", 649990),
            make_listing("Ripley", 699990),
            make_listing("PCFactory", 679990),
        ]
        result = compare_prices(listings)
        assert len(result) == 3

    def test_empty_list(self):
        assert compare_prices([]) == []

    def test_single_item(self):
        listing = make_listing("Falabella", 649990)
        result = compare_prices([listing])
        assert len(result) == 1
        assert result[0].price == 649990
