from datetime import date, timedelta
from decimal import Decimal
from app.services.rules import return_eligibility


class DummyOrder:
    status = "DELIVERED"
    delivered_date = date.today() - timedelta(days=2)
    order_id = "ORD-TEST"


class DummyQuery:
    def filter_by(self, **kwargs):
        return self

    def first(self):
        return None


class DummyDB:
    def query(self, model):
        return DummyQuery()


def test_return_eligibility():
    ok, message = return_eligibility(DummyDB(), DummyOrder())
    assert ok is True
    assert "return window" in message.lower()
