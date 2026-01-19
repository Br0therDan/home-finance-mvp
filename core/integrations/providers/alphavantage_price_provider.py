from __future__ import annotations
import requests
import streamlit as st
from datetime import datetime
from typing import List
from core.integrations.interfaces import PriceProvider, PriceQuote


class AlphaVantagePriceProvider(PriceProvider):
    """
    Alpha Vantage API Provider for Market Prices.
    Uses GLOBAL_QUOTE for simplicity (single symbol lookup).
    """

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self):
        self.api_key = st.secrets.get("ALPHA_VANTAGE_API_KEY")
        if not self.api_key:
            raise ValueError("ALPHA_VANTAGE_API_KEY not found in streamlit secrets.")

    def get_latest_prices(self, symbols: List[str], market: str) -> List[PriceQuote]:
        # Market "US" only for Alpha Vantage MVP
        if market.upper() != "US":
            return []

        quotes = []
        for symbol in symbols:
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": self.api_key,
            }
            try:
                response = requests.get(self.BASE_URL, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                quote_data = data.get("Global Quote")
                if not quote_data:
                    # Could be rate limit or invalid symbol
                    continue

                price = float(quote_data.get("05. price", 0))
                # Alpha Vantage GLOBAL_QUOTE doesn't provide currency in the response directly
                # usually it's USD for US symbols.
                currency = "USD"
                as_of = quote_data.get(
                    "07. latest trading day", datetime.now().strftime("%Y-%m-%d")
                )

                quotes.append(
                    PriceQuote(
                        symbol=symbol,
                        market=market,
                        currency=currency,
                        price=price,
                        as_of=as_of,
                        source="alphavantage",
                    )
                )
            except Exception as e:
                # Log or re-raise? Service layer should handle logging
                print(f"Error fetching {symbol} from Alpha Vantage: {e}")

        return quotes
