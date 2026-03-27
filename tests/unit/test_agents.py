"""Tests unitarios para los subagentes de DealScout."""


from src.agent.comparator import create_comparator_subagent
from src.agent.scraper import create_scraper_subagent
from src.agent.searcher import create_searcher_subagent

REQUIRED_KEYS = {"name", "description", "system_prompt", "tools"}


class TestSearcherSubagent:
    def setup_method(self):
        self.subagent = create_searcher_subagent()

    def test_has_required_keys(self):
        assert REQUIRED_KEYS.issubset(self.subagent.keys())

    def test_name(self):
        assert self.subagent["name"] == "searcher-agent"

    def test_has_tools(self):
        assert len(self.subagent["tools"]) > 0

    def test_tools_count(self):
        # Debe tener Solotodo + MercadoLibre + SerpAPI
        assert len(self.subagent["tools"]) == 3

    def test_system_prompt_mentions_chile(self):
        prompt = self.subagent["system_prompt"].lower()
        assert "chile" in prompt or "chileno" in prompt or "chilena" in prompt

    def test_system_prompt_mentions_clp(self):
        assert "CLP" in self.subagent["system_prompt"] or "pesos" in self.subagent["system_prompt"]

    def test_description_is_descriptive(self):
        assert len(self.subagent["description"]) > 50


class TestScraperSubagent:
    def setup_method(self):
        self.subagent = create_scraper_subagent()

    def test_has_required_keys(self):
        assert REQUIRED_KEYS.issubset(self.subagent.keys())

    def test_name(self):
        assert self.subagent["name"] == "scraper-agent"

    def test_has_tools(self):
        assert len(self.subagent["tools"]) > 0

    def test_tools_count(self):
        # extract_product_from_url + search_and_extract_from_site + scrape_with_browser
        assert len(self.subagent["tools"]) == 3

    def test_system_prompt_mentions_fallback(self):
        prompt = self.subagent["system_prompt"].lower()
        assert "fallback" in prompt or "playwright" in prompt or "firecrawl" in prompt

    def test_system_prompt_mentions_price_format(self):
        # Debe instruir sobre el formato de precios chilenos
        prompt = self.subagent["system_prompt"]
        assert "." in prompt and ("miles" in prompt.lower() or "separador" in prompt.lower())


class TestComparatorSubagent:
    def setup_method(self):
        self.subagent = create_comparator_subagent()

    def test_has_required_keys(self):
        assert REQUIRED_KEYS.issubset(self.subagent.keys())

    def test_name(self):
        assert self.subagent["name"] == "comparator-agent"

    def test_has_tools(self):
        assert len(self.subagent["tools"]) > 0

    def test_tools_include_price_history(self):
        tool_names = [t.name for t in self.subagent["tools"]]
        assert "get_price_history" in tool_names

    def test_system_prompt_mentions_tiendas_chilenas(self):
        prompt = self.subagent["system_prompt"]
        assert "Falabella" in prompt or "Ripley" in prompt

    def test_system_prompt_mentions_recommendation(self):
        prompt = self.subagent["system_prompt"].lower()
        assert "recomendacion" in prompt or "mejor" in prompt


class TestAllSubagentsUniqueness:
    def test_unique_names(self):
        names = [
            create_searcher_subagent()["name"],
            create_scraper_subagent()["name"],
            create_comparator_subagent()["name"],
        ]
        assert len(names) == len(set(names)), "Los subagentes deben tener nombres unicos"

    def test_no_shared_tools_between_searcher_and_scraper(self):
        searcher_tools = {t.name for t in create_searcher_subagent()["tools"]}
        scraper_tools = {t.name for t in create_scraper_subagent()["tools"]}
        # Searcher usa APIs, Scraper usa extraccion web — no deben compartir tools
        intersection = searcher_tools & scraper_tools
        assert len(intersection) == 0, f"Tools compartidas entre searcher y scraper: {intersection}"
