from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Integer, DateTime, Date, Numeric, Text, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    returnable: Mapped[bool] = mapped_column(Boolean, default=True)


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    customer_id: Mapped[str] = mapped_column(String(30), ForeignKey("customers.customer_id"))
    product_sku: Mapped[str] = mapped_column(String(50), ForeignKey("products.sku"))
    status: Mapped[str] = mapped_column(String(40))
    order_date: Mapped[date] = mapped_column(Date)
    delivered_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    damaged_reported: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_received: Mapped[bool] = mapped_column(Boolean, default=False)


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payment_id: Mapped[str] = mapped_column(String(30), unique=True)
    order_id: Mapped[str] = mapped_column(String(30), ForeignKey("orders.order_id"))
    status: Mapped[str] = mapped_column(String(40))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    refunded_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)


class ReturnRequest(Base):
    __tablename__ = "return_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    return_id: Mapped[str] = mapped_column(String(30), unique=True)
    order_id: Mapped[str] = mapped_column(String(30), ForeignKey("orders.order_id"))
    reason: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Refund(Base):
    __tablename__ = "refunds"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    refund_id: Mapped[str] = mapped_column(String(30), unique=True)
    order_id: Mapped[str] = mapped_column(String(30), ForeignKey("orders.order_id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SupportCase(Base):
    __tablename__ = "support_cases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[str] = mapped_column(String(30), unique=True)
    customer_id: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(Text)
    intent: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), default="OPEN")
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    escalation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[str] = mapped_column(String(30), index=True)
    event_type: Mapped[str] = mapped_column(String(80))
    details: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
