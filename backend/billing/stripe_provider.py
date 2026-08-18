"""Stripe billing provider."""

from __future__ import annotations

import logging
from typing import Any

import redis

from backend.billing.base import BillingProvider
from backend.config import settings

logger = logging.getLogger(__name__)


def _stripe():
    import stripe

    stripe.api_key = settings.stripe_secret_key
    return stripe


class StripeBillingProvider(BillingProvider):
    def __init__(self) -> None:
        self._redis = redis.from_url(settings.redis_url, decode_responses=True)

    def _price_id(self, plan: str) -> str:
        if plan == "annual":
            return settings.stripe_pro_annual_price_id
        return settings.stripe_pro_monthly_price_id

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
        params: dict[str, Any] = {
            "mode": "subscription",
            "line_items": [{"price": self._price_id(plan), "quantity": 1}],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "client_reference_id": user_id,
            "metadata": {"user_id": user_id, "plan": plan},
        }
        if customer_id:
            params["customer"] = customer_id
        else:
            params["customer_email"] = customer_email
        session = _stripe().checkout.Session.create(**params)
        return session.url or ""

    def create_portal_session(self, *, customer_id: str, return_url: str) -> str:
        session = _stripe().billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return session.url

    def handle_webhook(self, payload: bytes, signature: str | None) -> dict[str, Any]:
        if not settings.stripe_webhook_secret:
            return {"status": "ignored"}
        event = _stripe().Webhook.construct_event(
            payload, signature, settings.stripe_webhook_secret
        )
        event_id = event["id"]
        dedup_key = f"billing:event:{event_id}"
        if self._redis.exists(dedup_key):
            return {"status": "duplicate"}
        self._redis.setex(dedup_key, 86400 * 7, "1")

        etype = event["type"]
        data = event["data"]["object"]
        result: dict[str, Any] = {"status": "ok", "event_type": etype}

        if etype == "checkout.session.completed":
            user_id = data.get("client_reference_id") or data.get("metadata", {}).get("user_id")
            customer_id = data.get("customer")
            if user_id:
                result.update({"user_id": user_id, "plan_tier": "pro", "stripe_customer_id": customer_id})
        elif etype == "customer.subscription.deleted":
            customer_id = data.get("customer")
            result.update({"stripe_customer_id": customer_id, "plan_tier": "free"})
        elif etype == "invoice.payment_failed":
            customer_id = data.get("customer")
            result.update({"stripe_customer_id": customer_id, "event": "payment_failed"})

        return result


def get_billing_provider() -> BillingProvider:
    if settings.billing_provider.lower() == "lemonsqueezy":
        from backend.billing.lemonsqueezy_provider import LemonSqueezyProvider

        return LemonSqueezyProvider()
    return StripeBillingProvider()
