from pydantic import BaseModel, Field


class CheckoutSessionRequest(BaseModel):
    plan: str = Field(..., pattern="^(monthly|annual)$")


class CheckoutSessionResponse(BaseModel):
    checkout_url: str


class PortalSessionResponse(BaseModel):
    portal_url: str
