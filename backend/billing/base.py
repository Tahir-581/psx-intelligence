"""Pluggable billing provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BillingProvider(ABC):
    @abstractmethod
    def create_checkout_session(
        self,
        *,
        customer_id: str | None,
        customer_email: str,
        user_id: str,
        plan: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Return checkout URL."""

    @abstractmethod
    def create_portal_session(self, *, customer_id: str, return_url: str) -> str:
        """Return customer portal URL."""

    @abstractmethod
    def handle_webhook(self, payload: bytes, signature: str | None) -> dict[str, Any]:
        """Process webhook; return action dict with user_id/plan_tier updates."""
