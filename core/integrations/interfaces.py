from __future__ import annotations

from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import List


@dataclass
class FxRate:
    base_currency: str
    quote_currency: str
    rate: float
    as_of: str
    source: str


@dataclass
class PriceQuote:
    symbol: str
    market: str
    currency: str
    price: float
    as_of: str
    source: str


class FXProvider(ABC):
    @abstractmethod
    def get_latest_rates(self, base: str, quotes: List[str]) -> List[FxRate]:
        pass


class PriceProvider(ABC):
    @abstractmethod
    def get_latest_prices(self, symbols: List[str], market: str) -> List[PriceQuote]:
        pass
