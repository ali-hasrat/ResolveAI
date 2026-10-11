from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import os
import re
import uuid

from app.db.database import get_db
from app.models.models import SupportCase, Order
from app.agent.agent import run_agent, detect_intent
from app.services.audit import audit


router = APIRouter()


class SupportRequest(BaseModel):
    # Optional for general policy questions. Order-specific actions still
    # require a customer ID to be supplied before the agent can run.
    customer_id: str | None = None
    message: str = Field(..., min_length=1, max_length=5000)


ORDER_INTENTS = {
    "DAMAGED_PRODUCT",
    "REFUND",
    "RETURN",
    "DELIVERY",
    "PAYMENT",
    "CANCELLATION",
}

UPLOAD_DIR = "uploads/evidence"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/support")
def support(
    request: SupportRequest,
    db: Session = Depends(get_db),
):
    """Create a support case and run the AI support agent."""

    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Please enter a message.")

    case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
    intent = detect_intent(message)

    # Do not treat an ID mentioned in arbitrary prose as authenticated identity.
    # It is only used as a supplied identifier in this prototype.
    customer_id = (
        request.customer_id.strip().upper()
        if request.customer_id and request.customer_id.strip()
        else None
    )
    if not customer_id:
        customer_match = re.search(r"\bCUST-\d+\b", message.upper())
        if customer_match:
            customer_id = customer_match.group(0)

    # SupportCase.customer_id is non-null in the current database schema.
    # "GUEST" is a sentinel for anonymous policy/general questions only.
    case_customer_id = customer_id or "GUEST"

    case = SupportCase(
        case_id=case_id,
        customer_id=case_customer_id,
        message=message,
        intent=intent,
        status="OPEN",
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    # Do not call the agent for order operations without customer details.
    # This prevents passing a fake guest identity into order tools.
    if intent in ORDER_INTENTS and not customer_id:
        response = (
            "I can help with your order. Please include the customer ID "
            "registered to the order (for example, CUST-1001) and your order "
            "number in your message so I can check the request."
        )
        case.status = "WAITING_FOR_INFORMATION"
        case.resolution = response
        audit(
            db,
            case_id,
            "CUSTOMER_INFORMATION_REQUESTED",
            {
                "intent": intent,
                "required_information": ["customer_id", "order_id"],
            },
        )
        db.commit()
        db.refresh(case)

        return {
            "case_id": case.case_id,
            "status": case.status,
            "intent": intent,
            "response": response,
            "evidence": [],
            "actions": [],
            "escalation_reason": None,
        }

    result = run_agent(
        db=db,
        customer_id=customer_id or "GUEST",
        message=message,
        case_id=case_id,
        intent=intent,
    )

    case.status = result.get("status", "OPEN")
    case.resolution = result.get("response")
    case.escalation_reason = result.get("escalation_reason")

    db.commit()
    db.refresh(case)

    return {
        "case_id": case.case_id,
        "status": case.status,
        "intent": result.get("intent", intent),
        "response": result.get("response"),
        "evidence": result.get("evidence", []),
        "actions": result.get("actions", []),
        "escalation_reason": result.get("escalation_reason"),
    }


@router.post("/support/cases/{case_id}/evidence")
async def upload_evidence(
    case_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload photographic evidence for an eligible damaged-product case."""

    case = (
        db.query(SupportCase)
        .filter(SupportCase.case_id == case_id)
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail="Support case not found.")

    if case.intent != "DAMAGED_PRODUCT":
        raise HTTPException(
            status_code=400,
            detail="Photo evidence is only accepted for damaged-product cases.",
        )

    if case.customer_id == "GUEST":
        raise HTTPException(
            status_code=400,
            detail="Customer details are required before uploading evidence.",
        )

    allowed_types = {
        "image/jpeg": (".jpg", b"\xff\xd8\xff"),
        "image/png": (".png", b"\x89PNG\r\n\x1a\n"),
        "image/webp": (".webp", None),
    }
    content_type = (file.content_type or "").lower()
    if content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Please upload a JPG, PNG, or WebP image.",
        )

    contents = await file.read()
    max_size = 8 * 1024 * 1024

    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")
    if len(contents) > max_size:
        raise HTTPException(
            status_code=400,
            detail="Image must be smaller than 8 MB.",
        )

    extension, signature = allowed_types[content_type]
    if signature and not contents.startswith(signature):
        raise HTTPException(
            status_code=400,
            detail="The uploaded file content does not match its image type.",
        )
    if content_type == "image/webp" and not (
        contents.startswith(b"RIFF") and contents[8:12] == b"WEBP"
    ):
        raise HTTPException(
            status_code=400,
            detail="The uploaded file content does not match its image type.",
        )

    match = re.search(r"\bORD-\d+\b", case.message.upper())
    if not match:
        raise HTTPException(
            status_code=400,
            detail="No order number is associated with this case.",
        )

    order_id = match.group(0)
    order = (
        db.query(Order)
        .filter(Order.order_id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(
            status_code=404,
            detail="Associated order was not found.",
        )

    if order.customer_id != case.customer_id:
        raise HTTPException(
            status_code=403,
            detail="The associated order does not belong to this customer.",
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    unique_name = f"{case_id}_{uuid.uuid4().hex[:10]}{extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    try:
        with open(file_path, "wb") as buffer:
            buffer.write(contents)

        order.evidence_received = True
        order.damaged_reported = True
        db.commit()
        db.refresh(order)

        audit(
            db,
            case_id,
            "EVIDENCE_UPLOADED",
            {
                "filename": unique_name,
                "content_type": content_type,
                "size_bytes": len(contents),
                "order_id": order_id,
            },
        )

        result = run_agent(
            db=db,
            customer_id=case.customer_id,
            message=case.message,
            case_id=case.case_id,
            intent=case.intent,
        )

        case.status = result.get("status", "OPEN")
        case.resolution = result.get("response")
        case.escalation_reason = result.get("escalation_reason")
        db.commit()
        db.refresh(case)

    except Exception:
        db.rollback()
        # Avoid leaving an uploaded file behind when processing fails.
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        raise

    return {
        "success": True,
        "case_id": case.case_id,
        "status": case.status,
        "intent": result.get("intent", case.intent),
        "response": result.get("response"),
        "evidence": result.get("evidence", []),
        "actions": result.get("actions", []),
        "escalation_reason": result.get("escalation_reason"),
        "uploaded_file": unique_name,
    }
