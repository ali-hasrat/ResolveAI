from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.models import (
    SupportCase,
    Customer,
    Order,
)


router = APIRouter(
    prefix="/admin/cases",
    tags=["Support Agent"],
)


# ============================================================
# LIST ESCALATED CASES
# ============================================================

@router.get("")
def get_escalated_cases(
    status: str = "ESCALATED",
):
    """
    Return cases for the support-agent dashboard.

    By default only escalated cases are returned.
    """

    db = SessionLocal()

    try:

        cases = db.scalars(
            select(SupportCase)
            .where(
                SupportCase.status == status
            )
            .order_by(
                SupportCase.created_at.desc()
            )
        ).all()

        result = []

        for case in cases:

            customer = db.scalar(
                select(Customer).where(
                    Customer.customer_id
                    == case.customer_id
                )
            )

            result.append(
                {
                    "case_id": case.case_id,
                    "customer_id": case.customer_id,
                    "customer_name": (
                        customer.name
                        if customer
                        else None
                    ),
                    "customer_email": (
                        customer.email
                        if customer
                        else None
                    ),
                    "intent": case.intent,
                    "status": case.status,
                    "message": case.message,
                    "resolution": case.resolution,
                    "escalation_reason": (
                        case.escalation_reason
                    ),
                    "created_at": (
                        case.created_at.isoformat()
                        if case.created_at
                        else None
                    ),
                }
            )

        return {
            "count": len(result),
            "cases": result,
        }

    finally:
        db.close()


# ============================================================
# GET ONE CASE
# ============================================================

@router.get("/{case_id}")
def get_case_details(
    case_id: str,
):
    """
    Return complete information about one support case.
    """

    db = SessionLocal()

    try:

        case = db.scalar(
            select(SupportCase).where(
                SupportCase.case_id == case_id
            )
        )

        if not case:
            raise HTTPException(
                status_code=404,
                detail="Case not found.",
            )

        customer = db.scalar(
            select(Customer).where(
                Customer.customer_id
                == case.customer_id
            )
        )

        # Try to identify an order from the original
        # customer message.
        order = None

        import re

        match = re.search(
            r"\bORD-\d+\b",
            case.message.upper(),
        )

        if match:

            order_id = match.group(0)

            order = db.scalar(
                select(Order).where(
                    Order.order_id == order_id
                )
            )

        return {
            "case_id": case.case_id,

            "customer": {
                "customer_id": (
                    customer.customer_id
                    if customer
                    else case.customer_id
                ),
                "name": (
                    customer.name
                    if customer
                    else None
                ),
                "email": (
                    customer.email
                    if customer
                    else None
                ),
            },

            "order": (
                {
                    "order_id": order.order_id,
                    "status": order.status,
                    "order_date": (
                        order.order_date.isoformat()
                        if order.order_date
                        else None
                    ),
                    "delivered_date": (
                        order.delivered_date.isoformat()
                        if order.delivered_date
                        else None
                    ),
                    "total_amount": float(
                        order.total_amount
                    ),
                    "evidence_received": (
                        order.evidence_received
                    ),
                }
                if order
                else None
            ),

            "case": {
                "intent": case.intent,
                "status": case.status,
                "message": case.message,
                "resolution": case.resolution,
                "escalation_reason": (
                    case.escalation_reason
                ),
                "created_at": (
                    case.created_at.isoformat()
                    if case.created_at
                    else None
                ),
            },
        }

    finally:
        db.close()


# ============================================================
# RESOLVE CASE MANUALLY
# ============================================================

@router.post("/{case_id}/resolve")
def resolve_case(
    case_id: str,
    resolution: str,
):
    """
    Allow a human support representative to resolve
    an escalated case.

    The resolution is explicitly supplied by the human.
    """

    db = SessionLocal()

    try:

        case = db.scalar(
            select(SupportCase).where(
                SupportCase.case_id == case_id
            )
        )

        if not case:
            raise HTTPException(
                status_code=404,
                detail="Case not found.",
            )

        if case.status == "RESOLVED":
            return {
                "success": True,
                "message": (
                    "Case is already resolved."
                ),
                "case_id": case.case_id,
                "status": case.status,
            }

        if not resolution.strip():
            raise HTTPException(
                status_code=400,
                detail=(
                    "Resolution cannot be empty."
                ),
            )

        case.status = "RESOLVED"

        case.resolution = (
            resolution.strip()
        )

        db.commit()
        db.refresh(case)

        return {
            "success": True,
            "case_id": case.case_id,
            "status": case.status,
            "resolution": case.resolution,
            "message": (
                "Case resolved successfully."
            ),
        }

    finally:
        db.close()