from datetime import date

import requests
import streamlit as st


class AlphaVantageService:
    def __init__(self, api_key: str | None = None):
        if api_key:
            self.api_key = api_key
        else:
            # Fallback to streamlit secrets
            try:
                self.api_key = st.secrets.get("ALPHA_VANTAGE_API_KEY")
            except Exception:
                self.api_key = None

    def get_latest_price(self, ticker: str) -> dict | None:
        """Fetch latest price for a ticker using GLOBAL_QUOTE.

        Returns:
            dict: { "price": float, "as_of_date": date, "currency": str }
        """
        if not self.api_key:
            print("Alpha Vantage API Key not configured")
            return None

        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={self.api_key}"
        try:
            response = requests.get(url)
            data = response.json()

            quote = data.get("Global Quote")
            if not quote:
                print(f"No market data for {ticker}: {data}")
                return None

            price = float(quote.get("05. price"))
            latest_trading_day = quote.get("07. latest trading day")

            return {
                "price": price,
                "as_of_date": (
                    date.fromisoformat(latest_trading_day)
                    if latest_trading_day
                    else date.today()
                ),
                "currency": "USD",  # Alpha Vantage GLOBAL_QUOTE defaults to USD for most US stocks.
                # For local stocks like KRW, symbols usually end in .KSC or .KS
            }
        except Exception as e:
            print(f"Error fetching price for {ticker}: {e}")
            return None
