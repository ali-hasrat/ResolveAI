"""
ResolveAI Controlled Operational Tools

These functions form the safety boundary between the AI agent
and the database.

The AI agent can decide which operation is appropriate, but
these backend tools perform deterministic validation before
changing any business data.

Current database models:
    Customer
    Product
    Order
    Payment
    ReturnRequest
    Refund
    SupportCase
    AuditLog
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import (
    Customer,
    Product,
    Order,
    Payment,
    ReturnRequest,
    Refund,
    SupportCase,
)


# ============================================================
# HELPER
# ============================================================

def _generate_id(prefix: str) -> str:
    """Generate a short unique business ID."""

    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


# ============================================================
# CUSTOMER
# ============================================================

def get_customer(
    db: Session,
    customer_id: str,
):
    """
    Retrieve a customer.

    READ ONLY.
    """

    customer = db.scalar(
        select(Customer).where(
            Customer.customer_id == customer_id
        )
    )

    return customer


# ============================================================
# ORDER
# ============================================================

def get_order(
    db: Session,
    order_id: str,
):
    """
    Retrieve an Order object.

    The current agent.py expects an actual SQLAlchemy Order
    object because it accesses:

        order.order_id
        order.customer_id
        order.status
        order.total_amount
        order.delivered_date
        order.evidence_received
    """

    return db.scalar(
        select(Order).where(
            Order.order_id == order_id
        )
    )


# ============================================================
# PAYMENT
# ============================================================

def get_payment(
    db: Session,
    order_id: str,
):
    """
    Retrieve the payment associated with an order.

    READ ONLY.
    """

    return db.scalar(
        select(Payment).where(
            Payment.order_id == order_id
        )
    )


# ============================================================
# PRODUCT
# ============================================================

def get_product(
    db: Session,
    sku: str,
):
    """
    Retrieve product information.

    READ ONLY.
    """

    return db.scalar(
        select(Product).where(
            Product.sku == sku
        )
    )


# ============================================================
# ORDER HISTORY
# ============================================================

def get_order_history(
    db: Session,
    customer_id: str,
):
    """
    Retrieve all orders belonging to a customer.

    READ ONLY.
    """

    orders = db.scalars(
        select(Order)
        .where(
            Order.customer_id == customer_id
        )
        .order_by(
            Order.order_date.desc()
        )
    ).all()

    return orders


# ============================================================
# RETURN
# ============================================================

def create_return(
    db: Session,
    order,
    return_type: str = "CUSTOMER_RETURN",
) -> dict:
    """
    Create a return request.

    Backend validation:
        1. Order exists.
        2. Order is delivered.
        3. Order is within the 7-day return window.
        4. Duplicate return requests are prevented.

    This function creates a ReturnRequest record.
    """

    if not order:
        return {
            "success": False,
            "message": "Order not found.",
        }

    # --------------------------------------------------------
    # Check delivery status
    # --------------------------------------------------------

    if order.status != "DELIVERED":
        return {
            "success": False,
            "message": (
                "A return can only be created after "
                "the order has been delivered."
            ),
        }

    # --------------------------------------------------------
    # Check duplicate return
    # --------------------------------------------------------

    existing_return = db.scalar(
        select(ReturnRequest).where(
            ReturnRequest.order_id == order.order_id
        )
    )

    if existing_return:
        return {
            "success": False,
            "message": (
                f"A return request "
                f"{existing_return.return_id} already "
                "exists for this order."
            ),
        }

    # --------------------------------------------------------
    # Check delivery date
    # --------------------------------------------------------

    if not order.delivered_date:
        return {
            "success": False,
            "message": (
                "Delivery date is unavailable. "
                "Manual review is required."
            ),
        }

    days_since_delivery = (
        date.today() - order.delivered_date
    ).days

    # --------------------------------------------------------
    # 7-day return window
    # --------------------------------------------------------

    if days_since_delivery > 7:
        return {
            "success": False,
            "message": (
                "The order is outside the 7-day "
                "return window."
            ),
        }

    # --------------------------------------------------------
    # Create return request
    # --------------------------------------------------------

    return_id = _generate_id("RET")

    return_request = ReturnRequest(
        return_id=return_id,
        order_id=order.order_id,
        reason=return_type,
        status="REQUESTED",
    )

    db.add(return_request)
    db.commit()
    db.refresh(return_request)

    return {
        "success": True,
        "return_id": return_request.return_id,
        "return_type": return_type,
        "message": (
            f"Return request {return_request.return_id} "
            "created successfully."
        ),
    }


# ============================================================
# DAMAGED PRODUCT REPLACEMENT
# ============================================================

def create_replacement(
    db: Session,
    order,
) -> dict:
    """
    Create a replacement request for a damaged product.

    IMPORTANT:
    The current database does not contain a separate
    Replacement table.

    Therefore, a replacement is represented through the
    existing ReturnRequest table using:

        reason = DAMAGED_PRODUCT_REPLACEMENT

    Backend validation:
        1. Order exists.
        2. Order is delivered.
        3. Photo/evidence has been received.
        4. Order is within 7 days.
        5. No previous replacement request exists.
    """

    if not order:
        return {
            "success": False,
            "message": "Order not found.",
        }

    # --------------------------------------------------------
    # Delivered check
    # --------------------------------------------------------

    if order.status != "DELIVERED":
        return {
            "success": False,
            "message": (
                "A replacement can only be created "
                "after the order has been delivered."
            ),
        }

    # --------------------------------------------------------
    # Evidence check
    # --------------------------------------------------------

    if not order.evidence_received:
        return {
            "success": False,
            "message": (
                "Photographic evidence is required "
                "before creating a replacement."
            ),
        }

    # --------------------------------------------------------
    # Delivery date check
    # --------------------------------------------------------

    if not order.delivered_date:
        return {
            "success": False,
            "message": (
                "Delivery date is unavailable. "
                "Manual review is required."
            ),
        }

    days_since_delivery = (
        date.today() - order.delivered_date
    ).days

    # --------------------------------------------------------
    # 7-day replacement policy
    # --------------------------------------------------------

    if days_since_delivery > 7:
        return {
            "success": False,
            "message": (
                "The order is outside the 7-day "
                "replacement window."
            ),
        }

    # --------------------------------------------------------
    # Duplicate replacement check
    # --------------------------------------------------------

    existing_replacement = db.scalar(
        select(ReturnRequest).where(
            ReturnRequest.order_id == order.order_id,
            ReturnRequest.reason
            == "DAMAGED_PRODUCT_REPLACEMENT",
        )
    )

    if existing_replacement:
        return {
            "success": False,
            "message": (
                f"A replacement request "
                f"{existing_replacement.return_id} "
                "already exists for this order."
            ),
        }

    # --------------------------------------------------------
    # Create replacement request
    # --------------------------------------------------------

    replacement_id = _generate_id("REP")

    replacement_request = ReturnRequest(
        return_id=replacement_id,
        order_id=order.order_id,
        reason="DAMAGED_PRODUCT_REPLACEMENT",
        status="REQUESTED",
    )

    db.add(replacement_request)
    db.commit()
    db.refresh(replacement_request)

    return {
        "success": True,
        "replacement_id": replacement_id,
        "return_id": replacement_id,
        "message": (
            f"Replacement request {replacement_id} "
            "created successfully."
        ),
    }


# ============================================================
# REFUND
# ============================================================

def request_refund(
    db: Session,
    order,
    payment,
    amount: Decimal,
) -> dict:
    """
    Create a refund request.

    Backend validation:
        1. Order exists.
        2. Payment exists.
        3. Payment is successful.
        4. Duplicate refund is prevented.
        5. Refund amount cannot exceed payment amount.
        6. Refunds above INR 10,000 require human approval.
    """

    if not order:
        return {
            "success": False,
            "message": "Order not found.",
        }

    # --------------------------------------------------------
    # Payment check
    # --------------------------------------------------------

    if not payment:
        return {
            "success": False,
            "message": (
                "Payment information is unavailable."
            ),
        }

    # --------------------------------------------------------
    # Payment status
    # --------------------------------------------------------

    payment_status = (
        payment.status or ""
    ).upper()

    successful_statuses = {
        "SUCCESS",
        "SUCCEEDED",
        "COMPLETED",
        "PAID",
    }

    if payment_status not in successful_statuses:
        return {
            "success": False,
            "message": (
                "The payment was not successfully "
                "completed, so the refund cannot "
                "be created automatically."
            ),
        }

    # --------------------------------------------------------
    # Duplicate refund check
    # --------------------------------------------------------

    existing_refund = db.scalar(
        select(Refund).where(
            Refund.order_id == order.order_id
        )
    )

    if existing_refund:
        return {
            "success": False,
            "message": (
                f"A refund request "
                f"{existing_refund.refund_id} "
                "already exists for this order."
            ),
        }

    # --------------------------------------------------------
    # Amount validation
    # --------------------------------------------------------

    amount = Decimal(str(amount))

    if amount <= Decimal("0"):
        return {
            "success": False,
            "message": (
                "Refund amount must be greater than zero."
            ),
        }

    payment_amount = Decimal(
        str(payment.amount)
    )

    if amount > payment_amount:
        return {
            "success": False,
            "message": (
                "Refund amount cannot exceed the "
                "original payment amount."
            ),
        }

    # --------------------------------------------------------
    # High-value refund protection
    # --------------------------------------------------------

    if amount > Decimal("10000"):
        return {
            "success": False,
            "message": (
                "This refund exceeds the automatic "
                "refund limit of INR 10,000 and "
                "requires human approval."
            ),
        }

    # --------------------------------------------------------
    # Create refund
    # --------------------------------------------------------

    refund_id = _generate_id("REF")

    refund = Refund(
        refund_id=refund_id,
        order_id=order.order_id,
        amount=amount,
        status="REQUESTED",
    )

    db.add(refund)
    db.commit()
    db.refresh(refund)

    return {
        "success": True,
        "refund_id": refund.refund_id,
        "amount": float(refund.amount),
        "message": (
            f"Refund request {refund.refund_id} "
            "created successfully."
        ),
    }


# ============================================================
# CANCEL ORDER
# ============================================================

def cancel_order(
    db: Session,
    order_id: str,
) -> dict:
    """
    Cancel an order.

    Delivered orders cannot be automatically cancelled.
    """

    order = get_order(
        db,
        order_id,
    )

    if not order:
        return {
            "success": False,
            "message": "Order not found.",
        }

    if order.status == "DELIVERED":
        return {
            "success": False,
            "message": (
                "Delivered orders cannot be "
                "cancelled automatically."
            ),
        }

    if order.status == "CANCELLED":
        return {
            "success": False,
            "message": (
                "This order is already cancelled."
            ),
        }

    order.status = "CANCELLED"

    db.commit()
    db.refresh(order)

    return {
        "success": True,
        "status": "CANCELLED",
        "order_id": order.order_id,
        "message": (
            f"Order {order.order_id} has been "
            "cancelled successfully."
        ),
    }


# ============================================================
# SUPPORT ESCALATION
# ============================================================

def create_support_ticket(
    db: Session,
    customer_id: str,
    message: str,
    intent: str = "GENERAL",
    order_id: str | None = None,
    reason: str | None = None,
) -> dict:
    """
    Create a human-support case.

    Uses the actual SupportCase model from this project.
    """

    # --------------------------------------------------------
    # Customer verification
    # --------------------------------------------------------

    customer = get_customer(
        db,
        customer_id,
    )

    if not customer:
        return {
            "success": False,
            "message": "Customer not found.",
        }

    # --------------------------------------------------------
    # Generate case ID
    # --------------------------------------------------------

    case_id = _generate_id("CASE")

    # --------------------------------------------------------
    # Build case
    # --------------------------------------------------------

    case = SupportCase(
        case_id=case_id,
        customer_id=customer.customer_id,
        message=message,
        intent=intent,
        status="ESCALATED",
        resolution=None,
        escalation_reason=reason,
    )

    db.add(case)
    db.commit()
    db.refresh(case)

    return {
        "success": True,
        "case_id": case.case_id,
        "status": "ESCALATED",
        "message": (
            "Your case has been escalated to a "
            "human support representative."
        ),
        "reason": reason,
    }


# ============================================================
# TOOL REGISTRY
# ============================================================

TOOL_REGISTRY = {
    "get_customer": get_customer,
    "get_order": get_order,
    "get_payment": get_payment,
    "get_product": get_product,
    "get_order_history": get_order_history,
    "create_return": create_return,
    "create_replacement": create_replacement,
    "request_refund": request_refund,
    "cancel_order": cancel_order,
    "create_support_ticket": create_support_ticket,
}


def get_available_tools() -> list[str]:
    """
    Return the names of all tools available to ResolveAI.
    """

    return list(
        TOOL_REGISTRY.keys()
    )