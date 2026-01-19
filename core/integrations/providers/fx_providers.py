from __future__ import annotations
from typing import List
from core.integrations.interfaces import FXProvider, FxRate


class ManualFXProvider(FXProvider):
    """
    Manual FX Provider for MVP.
    Used to handle manual entries as a provider source.
    """

    def get_latest_rates(self, base: str, quotes: List[str]) -> List[FxRate]:
        # Manual provider doesn't 'fetch' externally.
        # It's used as a placeholder/registry entry for manual sync logic.
        return []


class EcosFxProvider(FXProvider):
    """
    Placeholder for future ECOS API implementation.
    """

    def get_latest_rates(self, base: str, quotes: List[str]) -> List[FxRate]:
        # TODO: Implement ECOS API integration
        return []
