from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.models import Order, Payment, Refund, ReturnRequest


def return_eligibility(db: Session, order: Order) -> tuple[bool, str]:
    if order.status != "DELIVERED":
        return False, "Order has not been delivered."
    if not order.delivered_date:
        return False, "Delivery date is unavailable."
    if (date.today() - order.delivered_date).days > 7:
        return False, "The 7-day return window has expired."
    if db.query(ReturnRequest).filter_by(order_id=order.order_id).first():
        return False, "A return already exists for this order."
    return True, "Order is within the return window."


def refund_eligibility(
    db: Session, order: Order, payment: Payment, amount: Decimal
) -> tuple[bool, str]:
    if payment.status != "PAID":
        return False, "Payment is not in PAID status."
    already = db.query(Refund).filter_by(order_id=order.order_id).first()
    if already:
        return False, "A refund already exists for this order."
    if amount <= 0:
        return False, "Refund amount must be positive."
    if amount > payment.amount:
        return False, "Refund cannot exceed the payment amount."
    if amount > Decimal("10000"):
        return False, "Refunds above INR 10,000 require human approval."
    return True, "Refund is eligible for automatic processing."
