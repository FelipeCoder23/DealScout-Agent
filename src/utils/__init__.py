"""Utilidades de DealScout."""

from src.utils.output import print_deal_result, print_error, print_searching_status
from src.utils.price import calculate_discount, compare_prices, format_clp, normalize_price

__all__ = [
    "normalize_price",
    "calculate_discount",
    "format_clp",
    "compare_prices",
    "print_deal_result",
    "print_searching_status",
    "print_error",
]
