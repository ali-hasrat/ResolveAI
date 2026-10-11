from pydantic import BaseModel, Field


class SupportRequest(BaseModel):
    customer_id: str = Field(..., examples=["CUST-1001"])
    message: str = Field(..., min_length=2)


class SupportResponse(BaseModel):
    case_id: str
    intent: str
    status: str
    response: str
    evidence: list[str] = []
    actions: list[str] = []
    escalation_reason: str | None = None
