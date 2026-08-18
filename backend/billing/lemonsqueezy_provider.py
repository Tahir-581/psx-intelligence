"""LemonSqueezy billing provider for PK-friendly payments."""

from __future__ import annotations

from typing import Any

import httpx

from backend.billing.base import BillingProvider
from backend.config import settings


class LemonSqueezyProvider(BillingProvider):
    BASE = "https://api.lemonsqueezy.com/v1"

    def create_checkout_session(
        self,
        *,
        customer_id: str | None = None,
        customer_email: str,
        user_id: str,
        plan: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        if not settings.lemonsqueezy_api_key:
            return ""
        import httpx

        resp = httpx.post(
            f"{self.BASE}/checkouts",
            headers={
                "Authorization": f"Bearer {settings.lemonsqueezy_api_key}",
                "Accept": "application/vnd.api+json",
                "Content-Type": "application/vnd.api+json",
            },
            json={
                "data": {
                    "type": "checkouts",
                    "attributes": {
                        "checkout_data": {"email": customer_email, "custom": {"user_id": user_id}},
                        "product_options": {"redirect_url": success_url},
                    },
                    "relationships": {
                        "store": {"data": {"type": "stores", "id": settings.lemonsqueezy_store_id}},
                        "variant": {
                            "data": {"type": "variants", "id": settings.lemonsqueezy_pro_variant_id}
                        },
                    },
                }
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["data"]["attributes"]["url"]

    def create_portal_session(self, *, customer_id: str, return_url: str) -> str:
        return return_url

    def handle_webhook(self, payload: bytes, signature: str | None) -> dict[str, Any]:
        if not settings.lemonsqueezy_webhook_secret:
            return {"action": "noop"}
        import hashlib
        import hmac
        import json

        expected = hmac.new(
            settings.lemonsqueezy_webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        if signature != expected:
            return {"action": "invalid_signature"}
        data = json.loads(payload)
        event = data.get("meta", {}).get("event_name")
        if event == "subscription_created":
            custom = data.get("meta", {}).get("custom_data", {})
            return {"status": "ok", "user_id": custom.get("user_id"), "plan_tier": "pro"}
        if event == "subscription_cancelled":
            custom = data.get("meta", {}).get("custom_data", {})
            return {"status": "ok", "user_id": custom.get("user_id"), "plan_tier": "free"}
        return {"status": "noop"}
