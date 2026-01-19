from __future__ import annotations


def krw(x: float) -> str:
    try:
        return f"₩{x:,.0f}"
    except Exception:
        return str(x)


def fmt(x: float, currency: str = "KRW") -> str:
    symbols = {
        "KRW": "₩",
        "USD": "$",
        "JPY": "¥",
        "EUR": "€",
    }
    symbol = symbols.get(currency.upper(), currency.upper() + " ")
    try:
        if currency.upper() in ["KRW", "JPY"]:
            return f"{symbol}{x:,.0f}"
        return f"{symbol}{x:,.2f}"
    except Exception:
        return str(x)
