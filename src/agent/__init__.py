"""Modulo de agentes de DealScout."""

from src.agent.comparator import create_comparator_subagent
from src.agent.scraper import create_scraper_subagent
from src.agent.searcher import create_searcher_subagent

__all__ = [
    "create_searcher_subagent",
    "create_scraper_subagent",
    "create_comparator_subagent",
]
