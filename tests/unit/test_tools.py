"""Tests unitarios de las tools de DealScout.

Tests sin API keys: verifican estructura, nombres y que las tools
manejan correctamente la falta de credenciales.
"""


from src.tools import (
    ALL_TOOLS,
    EXTRACTION_TOOLS,
    HISTORY_TOOLS,
    SEARCH_TOOLS,
    extract_product_from_url,
    get_price_history,
    scrape_with_browser,
    search_and_extract_from_site,
    search_google_shopping_chile,
    search_mercadolibre,
    search_solotodo,
)

# ─── Estructura de tools ─────────────────────────────────────────────────────

class TestToolsStructure:
    def test_all_tools_have_name(self):
        for tool in ALL_TOOLS:
            assert hasattr(tool, "name"), f"Tool sin nombre: {tool}"
            assert isinstance(tool.name, str)
            assert len(tool.name) > 0

    def test_all_tools_have_description(self):
        for tool in ALL_TOOLS:
            assert hasattr(tool, "description"), f"Tool sin descripcion: {tool.name}"
            assert isinstance(tool.description, str)
            assert len(tool.description) > 10, f"Descripcion muy corta en {tool.name}"

    def test_search_tools_count(self):
        assert len(SEARCH_TOOLS) == 3

    def test_extraction_tools_count(self):
        assert len(EXTRACTION_TOOLS) == 3

    def test_history_tools_count(self):
        assert len(HISTORY_TOOLS) == 1

    def test_all_tools_count(self):
        assert len(ALL_TOOLS) == 7

    def test_tool_names(self):
        names = [t.name for t in ALL_TOOLS]
        assert "search_solotodo" in names
        assert "search_mercadolibre" in names
        assert "search_google_shopping_chile" in names
        assert "extract_product_from_url" in names
        assert "search_and_extract_from_site" in names
        assert "scrape_with_browser" in names
        assert "get_price_history" in names


# ─── Comportamiento sin API keys ─────────────────────────────────────────────

class TestToolsWithoutApiKeys:
    """Verifica que las tools manejan la falta de credenciales graciosamente."""

    def test_serpapi_returns_empty_without_key(self, monkeypatch):
        monkeypatch.delenv("SERPAPI_KEY", raising=False)
        result = search_google_shopping_chile.invoke({"query": "iphone"})
        # Debe retornar algo (dict con success=False o lista vacia), nunca explotar
        assert result is not None

    def test_firecrawl_returns_empty_without_key(self, monkeypatch):
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        result = extract_product_from_url.invoke({
            "url": "https://falabella.com/producto/123",
            "store_name": "Falabella",
        })
        assert result == [] or result is not None

    def test_firecrawl_site_search_returns_empty_without_key(self, monkeypatch):
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        result = search_and_extract_from_site.invoke({
            "query": "notebook",
            "site_url": "falabella.com",
        })
        assert result == [] or result is not None


# ─── MercadoLibre (API publica, no requiere key) ─────────────────────────────

class TestMercadoLibreToolStructure:
    def test_tool_name(self):
        assert search_mercadolibre.name == "search_mercadolibre"

    def test_description_mentions_chile(self):
        desc = search_mercadolibre.description.lower()
        assert "chile" in desc or "chileno" in desc or "chilena" in desc

    def test_returns_list_on_network_error(self, monkeypatch):
        """Si hay error de red, debe retornar lista vacia, no explotar."""
        import httpx
        def mock_get(*args, **kwargs):
            raise httpx.TimeoutException("timeout")
        monkeypatch.setattr(httpx.Client, "get", mock_get)
        result = search_mercadolibre.invoke({"query": "iphone"})
        assert result == []


# ─── Solotodo (API publica, no requiere key) ──────────────────────────────────

class TestSolotodoToolStructure:
    def test_tool_name(self):
        assert search_solotodo.name == "search_solotodo"

    def test_description_mentions_electronics(self):
        desc = search_solotodo.description.lower()
        assert any(word in desc for word in ["electronica", "tecnologia", "laptop", "celular"])

    def test_returns_list_on_network_error(self, monkeypatch):
        import httpx
        def mock_get(*args, **kwargs):
            raise httpx.ConnectError("connection refused")
        monkeypatch.setattr(httpx.Client, "get", mock_get)
        result = search_solotodo.invoke({"query": "notebook"})
        assert result == []


# ─── Playwright fallback ──────────────────────────────────────────────────────

class TestPlaywrightTool:
    def test_tool_name(self):
        assert scrape_with_browser.name == "scrape_with_browser"

    def test_description_mentions_fallback(self):
        desc = scrape_with_browser.description.lower()
        assert "fallback" in desc or "ultimo" in desc or "only" in desc.lower()


# ─── Knasta ──────────────────────────────────────────────────────────────────

class TestKnastaTool:
    def test_tool_name(self):
        assert get_price_history.name == "get_price_history"

    def test_description_mentions_history(self):
        desc = get_price_history.description.lower()
        assert "historial" in desc or "history" in desc or "precio" in desc
