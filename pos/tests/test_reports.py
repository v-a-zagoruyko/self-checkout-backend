import pytest
from core.utils.reports import build_daily_report
from pos.tests.factories import OrderFactory, OrderItemFactory, PointOfSaleFactory

@pytest.mark.django_db
def test_build_daily_report_counts_and_pos():
	pos1 = PointOfSaleFactory(name="POS A")
	pos2 = PointOfSaleFactory(name="POS B")
	order1 = OrderFactory(pos=pos1, state="PAID")
	OrderItemFactory(order=order1, total_price=200)
	order2 = OrderFactory(pos=pos2, state="CANCELLED")
	OrderItemFactory(order=order2, total_price=100)
	report = build_daily_report()
	assert report["total_orders"] == 2
	assert report["total_paid"] == 1
	assert any("POS A" in s["pos_name"] for s in report["pos_stats"])
