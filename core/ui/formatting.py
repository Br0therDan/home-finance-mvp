from __future__ import annotations


def krw(x: float) -> str:
    try:
        return f"₩{x:,.0f}"
    except Exception:
        return str(x)
