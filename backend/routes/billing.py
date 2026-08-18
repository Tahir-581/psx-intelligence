from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.clerk_jwt import update_clerk_plan_metadata
from backend.auth.dependencies import require_user
from backend.billing.stripe_provider import get_billing_provider
from backend.config import settings
from backend.database import get_db
from backend.models.user import User
from backend.schemas.billing import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    PortalSessionResponse,
)

router = APIRouter(tags=["billing"])


@router.post("/billing/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    body: CheckoutSessionRequest,
    request: Request,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> CheckoutSessionResponse:
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing not configured")
    origin = request.headers.get("origin", "http://localhost:3000")
    provider = get_billing_provider()
    url = provider.create_checkout_session(
        customer_id=user.stripe_customer_id,
        customer_email=user.email,
        user_id=user.id,
        plan=body.plan,
        success_url=f"{origin}/account?checkout=success",
        cancel_url=f"{origin}/pricing?checkout=cancelled",
    )
    return CheckoutSessionResponse(checkout_url=url)


@router.get("/billing/portal", response_model=PortalSessionResponse)
async def billing_portal(
    request: Request,
    user: User = Depends(require_user),
) -> PortalSessionResponse:
    if not user.stripe_customer_id or not settings.stripe_secret_key:
        raise HTTPException(status_code=400, detail="No billing account found")
    origin = request.headers.get("origin", "http://localhost:3000")
    provider = get_billing_provider()
    url = provider.create_portal_session(
        customer_id=user.stripe_customer_id,
        return_url=f"{origin}/account",
    )
    return PortalSessionResponse(portal_url=url)


@router.post("/billing/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    stripe_signature: str | None = Header(None, alias="Stripe-Signature"),
) -> dict:
    payload = await request.body()
    provider = get_billing_provider()
    result = provider.handle_webhook(payload, stripe_signature)

    if result.get("user_id") and result.get("plan_tier"):
        values: dict = {"plan_tier": result["plan_tier"]}
        if result.get("stripe_customer_id"):
            values["stripe_customer_id"] = result["stripe_customer_id"]
        await db.execute(update(User).where(User.id == result["user_id"]).values(**values))
        await db.commit()
        update_clerk_plan_metadata(result["user_id"], result["plan_tier"])
    elif result.get("stripe_customer_id") and result.get("plan_tier"):
        await db.execute(
            update(User)
            .where(User.stripe_customer_id == result["stripe_customer_id"])
            .values(plan_tier=result["plan_tier"])
        )
        await db.commit()
        user = await db.scalar(
            select(User).where(User.stripe_customer_id == result["stripe_customer_id"])
        )
        if user:
            update_clerk_plan_metadata(user.id, result["plan_tier"])

    return {"status": result.get("status", "ok")}
