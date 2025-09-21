import pytest
from django.utils import timezone
from pos.tests.factories import OrderFactory, OrderItemFactory

@pytest.mark.django_db
def test_order_recalculate_total():
	order = OrderFactory()
	OrderItemFactory(order=order, total_price=50)
	OrderItemFactory(order=order, total_price=150)
	order.recalculate_total()
	assert order.total_price == 200