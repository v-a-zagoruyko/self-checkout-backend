import pytest
from core.tasks import archive_created_orders
from pos.tests.factories import OrderFactory

@pytest.mark.django_db
def test_archive_created_orders_archives():
	order = OrderFactory(state="CREATED")
	archive_created_orders()
	order.refresh_from_db()
	assert order.state == "ARCHIEVE"
