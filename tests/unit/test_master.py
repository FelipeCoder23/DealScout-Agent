"""Tests unitarios del master agent de DealScout."""

import pytest

from src.agent.master import create_dealscout_agent


class TestMasterAgent:
    def test_agent_can_be_created(self, monkeypatch):
        """El agente se puede crear con una API key configurada."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-fake")
        agent = create_dealscout_agent()
        assert agent is not None

    def test_agent_has_invoke_method(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-fake")
        agent = create_dealscout_agent()
        assert hasattr(agent, "invoke")

    def test_master_system_prompt_mentions_chile(self, monkeypatch):
        """El system prompt debe contextualizar el agente en Chile."""
        from src.agent.master import _MASTER_SYSTEM_PROMPT
        prompt_lower = _MASTER_SYSTEM_PROMPT.lower()
        assert "chile" in prompt_lower or "chileno" in prompt_lower

    def test_master_system_prompt_mentions_clp(self, monkeypatch):
        """El system prompt debe mencionar CLP para precios chilenos."""
        from src.agent.master import _MASTER_SYSTEM_PROMPT
        assert "CLP" in _MASTER_SYSTEM_PROMPT or "pesos" in _MASTER_SYSTEM_PROMPT

    def test_master_system_prompt_mentions_subagents(self, monkeypatch):
        """El system prompt debe mencionar el flujo con subagentes."""
        from src.agent.master import _MASTER_SYSTEM_PROMPT
        assert "searcher" in _MASTER_SYSTEM_PROMPT.lower() or "comparator" in _MASTER_SYSTEM_PROMPT.lower()

    def test_run_search_fails_without_api_key(self, monkeypatch):
        """run_search debe lanzar ValueError si falta ANTHROPIC_API_KEY."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from src.agent.master import run_search
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            run_search("iPhone 15")
