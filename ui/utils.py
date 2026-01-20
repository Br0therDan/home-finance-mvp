from __future__ import annotations

import streamlit as st

CURRENCY_CONFIG = {
    "KRW": {"symbol": "₩", "format": "%d", "step": 1, "precision": 0},
    "USD": {"symbol": "$", "format": "%.2f", "step": 0.01, "precision": 2},
    "JPY": {"symbol": "¥", "format": "%d", "step": 1, "precision": 0},
    "EUR": {"symbol": "€", "format": "%.2f", "step": 0.01, "precision": 2},
}

DEFAULT_CURRENCY = "KRW"


def get_currency_config(currency: str | None) -> dict:
    """Get formatting config for a given currency code."""
    currency = currency.upper() if currency else DEFAULT_CURRENCY
    return CURRENCY_CONFIG.get(currency, CURRENCY_CONFIG[DEFAULT_CURRENCY])


def get_pandas_style_fmt(currency: str | None) -> str:
    """Get pandas style format string (e.g. '₩ {:,.0f}')."""
    config = get_currency_config(currency)
    symbol = config["symbol"]
    precision = config["precision"]
    return f"{symbol} {{:,.{precision}f}}"


def format_currency(value: float | int, currency: str | None) -> str:
    """Format a number as a currency string (e.g., '₩ 1,000' or '$ 10.50')."""
    config = get_currency_config(currency)
    symbol = config["symbol"]
    precision = config["precision"]

    # Use standard f-string formatting for commas and precision
    formatted_num = f"{value:,.{precision}f}"
    return f"{symbol} {formatted_num}"
