"""Tests unitarios para el modo de busqueda rapida."""

from unittest.mock import patch

import pytest

from src.fast_search import _build_recommendation, run_fast_search
from src.schemas.product import DealResult, ProductListing

# ─── Helpers ──────────────────────────────────────────────────────────────


def _make_listing(**overrides) -> ProductListing:
    """Crea un ProductListing de prueba con valores por defecto."""
    defaults = {
        "name": "PlayStation 5",
        "price": 599990,
        "store": "MercadoLibre (Tienda Oficial)",
        "url": "https://www.mercadolibre.cl/ps5/p/MLC12345",
        "source": "mercadolibre_api",
    }
    defaults.update(overrides)
    return ProductListing(**defaults)


def _ml_results():
    return [
        _make_listing(price=599990, store="ML Vendedor 1", url="https://www.mercadolibre.cl/p/1").model_dump(),
        _make_listing(price=649990, store="ML Vendedor 2", url="https://www.mercadolibre.cl/p/2").model_dump(),
    ]


def _st_results():
    return [
        _make_listing(price=619990, store="PCFactory", url="https://pcfactory.cl/p/1", source="solotodo_api").model_dump(),
    ]


# ─── Tests de _build_recommendation ──────────────────────────────────────


class TestBuildRecommendation:
    def test_basic_recommendation(self):
        best = _make_listing(price=599990, store="MercadoLibre")
        alts = [_make_listing(price=649990, store="Falabella", url="https://falabella.com/p/1")]
        rec = _build_recommendation(best, alts)
        assert "$599.990" in rec
        assert "MercadoLibre" in rec

    def test_includes_savings_vs_alternative(self):
        best = _make_listing(price=500000, store="PCFactory")
        alts = [_make_listing(price=600000, store="Ripley", url="https://ripley.cl/p/1")]
        rec = _build_recommendation(best, alts)
        assert "$100.000" in rec
        assert "Ripley" in rec

    def test_includes_free_shipping(self):
        best = _make_listing(price=500000, shipping_info="Envio gratis")
        alts = [_make_listing(price=600000, url="https://other.cl/p/1")]
        rec = _build_recommendation(best, alts)
        assert "envio gratis" in rec.lower()

    def test_includes_discount(self):
        best = _make_listing(price=500000, original_price=700000)
        alts = [_make_listing(price=600000, url="https://other.cl/p/1")]
        rec = _build_recommendation(best, alts)
        assert "descuento" in rec.lower()

    def test_includes_rating(self):
        best = _make_listing(price=500000, rating=4.8)
        alts = [_make_listing(price=600000, url="https://other.cl/p/1")]
        rec = _build_recommendation(best, alts)
        assert "4.8" in rec

    def test_no_extras_when_none(self):
        best = _make_listing(price=500000)
        alts = [_make_listing(price=500000)]
        rec = _build_recommendation(best, alts)
        assert "Ademas" not in rec

    def test_same_price_no_savings_line(self):
        best = _make_listing(price=500000, store="Store A")
        alts = [_make_listing(price=500000, store="Store B")]
        rec = _build_recommendation(best, alts)
        assert "menos" not in rec


# ─── Tests de run_fast_search (con APIs mockeadas) ────────────────────────


class TestRunFastSearch:
    @patch("src.fast_search.search_google_shopping_chile")
    @patch("src.fast_search.search_solotodo")
    @patch("src.fast_search.search_mercadolibre")
    def test_returns_deal_result(self, mock_ml, mock_st, mock_gs, monkeypatch):
        monkeypatch.delenv("SERPAPI_KEY", raising=False)
        mock_ml.invoke.return_value = _ml_results()
        mock_st.invoke.return_value = _st_results()
        result = run_fast_search("PS5")
        assert isinstance(result, DealResult)
        assert result.best_deal.price == 599990

    @patch("src.fast_search.search_google_shopping_chile")
    @patch("src.fast_search.search_solotodo")
    @patch("src.fast_search.search_mercadolibre")
    def test_alternatives_sorted_by_price(self, mock_ml, mock_st, mock_gs, monkeypatch):
        monkeypatch.delenv("SERPAPI_KEY", raising=False)
        mock_ml.invoke.return_value = _ml_results()
        mock_st.invoke.return_value = _st_results()
        result = run_fast_search("PS5")
        alt_prices = [a.price for a in result.alternatives]
        assert alt_prices == sorted(alt_prices)

    @patch("src.fast_search.search_google_shopping_chile")
    @patch("src.fast_search.search_solotodo")
    @patch("src.fast_search.search_mercadolibre")
    def test_respects_budget_filter(self, mock_ml, mock_st, mock_gs, monkeypatch):
        monkeypatch.delenv("SERPAPI_KEY", raising=False)
        mock_ml.invoke.return_value = _ml_results()
        mock_st.invoke.return_value = _st_results()
        result = run_fast_search("PS5", max_budget=620000)
        assert result.best_deal.price <= 620000
        for alt in result.alternatives:
            assert alt.price <= 620000

    @patch("src.fast_search.search_google_shopping_chile")
    @patch("src.fast_search.search_solotodo")
    @patch("src.fast_search.search_mercadolibre")
    def test_raises_when_no_results(self, mock_ml, mock_st, mock_gs, monkeypatch):
        monkeypatch.delenv("SERPAPI_KEY", raising=False)
        mock_ml.invoke.return_value = []
        mock_st.invoke.return_value = []
        with pytest.raises(RuntimeError, match="No se encontraron"):
            run_fast_search("producto inexistente xyz")

    @patch("src.fast_search.search_google_shopping_chile")
    @patch("src.fast_search.search_solotodo")
    @patch("src.fast_search.search_mercadolibre")
    def test_sources_tracked(self, mock_ml, mock_st, mock_gs, monkeypatch):
        monkeypatch.delenv("SERPAPI_KEY", raising=False)
        mock_ml.invoke.return_value = _ml_results()
        mock_st.invoke.return_value = _st_results()
        result = run_fast_search("PS5")
        assert "MercadoLibre API" in result.sources_consulted
        assert "Solotodo API" in result.sources_consulted

    @patch("src.fast_search.search_google_shopping_chile")
    @patch("src.fast_search.search_solotodo")
    @patch("src.fast_search.search_mercadolibre")
    def test_survives_one_api_failure(self, mock_ml, mock_st, mock_gs, monkeypatch):
        monkeypatch.delenv("SERPAPI_KEY", raising=False)
        mock_ml.invoke.return_value = _ml_results()
        mock_st.invoke.side_effect = Exception("connection timeout")
        result = run_fast_search("PS5")
        assert isinstance(result, DealResult)
        assert "MercadoLibre API" in result.sources_consulted
        assert "Solotodo API" not in result.sources_consulted

    @patch("src.fast_search.search_google_shopping_chile")
    @patch("src.fast_search.search_solotodo")
    @patch("src.fast_search.search_mercadolibre")
    def test_duration_is_measured(self, mock_ml, mock_st, mock_gs, monkeypatch):
        monkeypatch.delenv("SERPAPI_KEY", raising=False)
        mock_ml.invoke.return_value = _ml_results()
        mock_st.invoke.return_value = []
        result = run_fast_search("PS5")
        assert result.search_duration_seconds >= 0
        assert result.search_duration_seconds < 60

    @patch("src.fast_search.search_google_shopping_chile")
    @patch("src.fast_search.search_solotodo")
    @patch("src.fast_search.search_mercadolibre")
    def test_single_result_still_works(self, mock_ml, mock_st, mock_gs, monkeypatch):
        monkeypatch.delenv("SERPAPI_KEY", raising=False)
        mock_ml.invoke.return_value = [_make_listing(price=599990).model_dump()]
        mock_st.invoke.return_value = []
        result = run_fast_search("PS5")
        assert isinstance(result, DealResult)
        assert len(result.alternatives) >= 1
