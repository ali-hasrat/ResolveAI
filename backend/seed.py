from datetime import date, timedelta
from decimal import Decimal
from app.db.database import Base, engine, SessionLocal
from app.models.models import Customer, Product, Order, Payment


Base.metadata.create_all(bind=engine)
db = SessionLocal()

try:
    if db.query(Customer).count() == 0:
        customer = Customer(
            customer_id="CUST-1001",
            name="Demo Customer",
            email="demo@resolveai.local",
        )
        db.add(customer)

        products = [
            Product(sku="SKU-HEADPHONE", name="Wireless Headphones", price=Decimal("7999"), returnable=True),
            Product(sku="SKU-CASE", name="Premium Phone Case", price=Decimal("1499"), returnable=True),
            Product(sku="SKU-LAPTOP", name="Developer Laptop", price=Decimal("89999"), returnable=True),
        ]
        db.add_all(products)
        db.flush()

        orders = [
            Order(
                order_id="ORD-48392",
                customer_id="CUST-1001",
                product_sku="SKU-HEADPHONE",
                status="DELIVERED",
                order_date=date.today() - timedelta(days=4),
                delivered_date=date.today() - timedelta(days=2),
                total_amount=Decimal("7999"),
                damaged_reported=True,
                evidence_received=False,
            ),
            Order(
                order_id="ORD-48393",
                customer_id="CUST-1001",
                product_sku="SKU-CASE",
                status="DELIVERED",
                order_date=date.today() - timedelta(days=5),
                delivered_date=date.today() - timedelta(days=3),
                total_amount=Decimal("1499"),
            ),
            Order(
                order_id="ORD-48394",
                customer_id="CUST-1001",
                product_sku="SKU-LAPTOP",
                status="SHIPPED",
                order_date=date.today() - timedelta(days=2),
                delivered_date=None,
                total_amount=Decimal("89999"),
            ),
        ]
        db.add_all(orders)
        db.flush()

        db.add_all([
            Payment(payment_id="PAY-48392", order_id="ORD-48392", status="PAID", amount=Decimal("7999")),
            Payment(payment_id="PAY-48393", order_id="ORD-48393", status="PAID", amount=Decimal("1499")),
            Payment(payment_id="PAY-48394", order_id="ORD-48394", status="PAID", amount=Decimal("89999")),
        ])

        db.commit()
        print("Seed data created.")
    else:
        print("Seed data already exists.")
finally:
    db.close()
