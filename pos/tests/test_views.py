import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from pos.tests.factories import OrderFactory, PaymentFactory, ProductFactory, StockFactory, PointOfSaleFactory


@pytest.mark.django_db
def test_product_by_barcode_no_pos_code(auth_client):
    product = ProductFactory()
    url = reverse("product-by-barcode", args=[product.barcode])
    res = auth_client.get(url)
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert res.json() == {"error": "Не указан код точки продаж"}


@pytest.mark.django_db
def test_product_by_barcode_invalid_pos_code(auth_client):
    product = ProductFactory()
    url = reverse("product-by-barcode", args=[product.barcode])
    res = auth_client.get(url, {"pos_code": "invalid"})
    assert res.status_code == status.HTTP_404_NOT_FOUND
    assert res.json() == {"error": "Точка продаж не найдена"}


@pytest.mark.django_db
def test_product_by_barcode_not_in_stock(auth_client):
    pos = PointOfSaleFactory()
    product = ProductFactory()
    url = reverse("product-by-barcode", args=[product.barcode])
    res = auth_client.get(url, {"pos_code": pos.code})
    assert res.status_code == status.HTTP_404_NOT_FOUND
    assert res.json() == {"error": "Товар не найден или недоступен"}


@pytest.mark.django_db
def test_product_by_barcode_inactive_stock(auth_client):
    pos = PointOfSaleFactory()
    product = ProductFactory()
    stock = StockFactory(pos=pos, product=product, is_active=False)
    url = reverse("product-by-barcode", args=[product.barcode])
    res = auth_client.get(url, {"pos_code": pos.code})
    assert res.status_code == status.HTTP_404_NOT_FOUND
    assert res.json() == {"error": "Товар не найден или недоступен"}


@pytest.mark.django_db
def test_product_by_barcode_success(auth_client):
    pos = PointOfSaleFactory()
    product = ProductFactory()
    stock = StockFactory(pos=pos, product=product, is_active=True)
    url = reverse("product-by-barcode", args=[product.barcode])
    res = auth_client.get(url, {"pos_code": pos.code})
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["name"] == product.name
    assert data["price"] == str(product.price)
    assert data["category"] == product.category.name


@pytest.mark.django_db
def test_create_order_invalid_data(auth_client):
    url = reverse("create-order")
    res = auth_client.post(url, {"pos_code": "", "order": []})
    assert res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_order_pos_not_found(auth_client):
    url = reverse("create-order")
    res = auth_client.post(url, {"pos_code": "invalid", "order": []}, format="json")
    assert res.status_code == status.HTTP_404_NOT_FOUND
    assert res.json() == {"error": "Точка продаж не найдена"}


@pytest.mark.django_db
def test_create_order_product_not_found(auth_client):
    pos = PointOfSaleFactory()
    url = reverse("create-order")
    res = auth_client.post(url, {"pos_code": pos.code, "order": [{"barcode": "not_exist", "quantity": 1}]}, format="json")
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "Продукт с штрихкодом not_exist не найден" in res.json()["error"]


@pytest.mark.django_db
def test_create_order_insufficient_stock(auth_client):
    pos = PointOfSaleFactory()
    product = ProductFactory()
    stock = StockFactory(pos=pos, product=product, quantity=0, is_active=True)
    url = reverse("create-order")
    res = auth_client.post(url, {"pos_code": pos.code, "order": [{"barcode": product.barcode, "quantity": 1}]}, format="json")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "order_id" in data
    assert "total_price" in data


@pytest.mark.django_db
def test_create_order_success(auth_client):
	pos = PointOfSaleFactory()
	product = ProductFactory()
	stock = StockFactory(pos=pos, product=product, quantity=10, is_active=True)
	url = reverse("create-order")
	res = auth_client.post(url, {"pos_code": pos.code, "order": [{"barcode": product.barcode, "quantity": 2}]}, format="json")
	assert res.status_code == status.HTTP_200_OK
	data = res.json()
	assert "order_id" in data
	assert data["total_price"] == Decimal(product.price * 2)
	stock.refresh_from_db()
	assert stock.quantity == 8


@pytest.mark.django_db
def test_create_payment_creates_new(auth_client):
	order = OrderFactory()
	url = reverse("create-payment")
	res = auth_client.post(url, {"order_id": order.id, "payment_type": "card"})
	assert res.status_code == status.HTTP_200_OK
	data = res.json()
	assert "payment_id" in data
	assert "payment_link" in data


@pytest.mark.django_db
def test_create_payment_fails_if_paid_exists(auth_client):
	order = OrderFactory()
	PaymentFactory(order=order, state="PAID")
	url = reverse("create-payment")
	res = auth_client.post(url, {"order_id": order.id, "payment_type": "card"})
	assert res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_payment_multiple_types(auth_client):
	order = OrderFactory()
	url = reverse("create-payment")

	res1 = auth_client.post(url, {"order_id": order.id, "payment_type": "card"})
	res2 = auth_client.post(url, {"order_id": order.id, "payment_type": "sbp"})

	data1 = res1.json()
	data2 = res2.json()

	assert res1.status_code == 200
	assert res2.status_code == 200
	assert data1["payment_id"] != data2["payment_id"]


@pytest.mark.django_db
def test_create_payment_returns_existing(auth_client):
	order = OrderFactory()
	payment = PaymentFactory(order=order, type="card")
	url = reverse("create-payment")
	res = auth_client.post(url, {"order_id": order.id, "payment_type": "card"})
	assert res.status_code == status.HTTP_200_OK
	assert res.json()["payment_id"] == payment.id


@pytest.mark.django_db
def test_create_payment_order_not_found(auth_client):
	url = reverse("create-payment")
	res = auth_client.post(url, {"order_id": 9999, "payment_type": "card"})
	assert res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_create_payment_existing_pending_different_type(auth_client):
	order = OrderFactory()
	PendingPayment = PaymentFactory(order=order, type="card", state="PENDING")
	url = reverse("create-payment")
	res = auth_client.post(url, {"order_id": order.id, "payment_type": "sbp"})
	data = res.json()
	assert res.status_code == 200
	assert data["payment_id"] != PendingPayment.id


@pytest.mark.django_db
def test_create_payment_invalid_type(auth_client):
	order = OrderFactory()
	url = reverse("create-payment")
	res = auth_client.post(url, {"order_id": order.id, "payment_type": "bitcoin"})
	assert res.status_code == status.HTTP_400_BAD_REQUEST
	assert res.json()["error"] == "Неправильный payment_type"


@pytest.mark.django_db
def test_mark_payment_paid_success(api_client):
	order = OrderFactory()
	payment = PaymentFactory(order=order, state="PENDING")
	url = reverse("mark-payment-paid")
	res = api_client.post(url, {"order_id": order.id})
	assert res.status_code == status.HTTP_200_OK
	payment.refresh_from_db()
	assert payment.state == "PAID"


@pytest.mark.django_db
def test_mark_payment_paid_already_paid(api_client):
	order = OrderFactory()
	payment = PaymentFactory(order=order, state="PAID")
	url = reverse("mark-payment-paid")
	res = api_client.post(url, {"order_id": order.id})
	assert res.status_code == status.HTTP_200_OK
	assert res.json()["message"] == "Оплата уже помечена как PAID"


@pytest.mark.django_db
def test_mark_payment_paid_no_pending(api_client):
	order = OrderFactory()
	url = reverse("mark-payment-paid")
	res = api_client.post(url, {"order_id": order.id})
	assert res.status_code == 404
	assert res.json()["error"] == "Нет PENDING платежа"


@pytest.mark.django_db
def test_mark_payment_paid_order_not_found(api_client):
	url = reverse("mark-payment-paid")
	res = api_client.post(url, {"order_id": 999})
	assert res.status_code == 404
	assert res.json()["error"] == "Заказ не найден"


@pytest.mark.django_db
def test_mark_payment_failed_success(api_client):
	order = OrderFactory()
	payment = PaymentFactory(order=order, state="PENDING")
	url = reverse("mark-payment-failed")
	res = api_client.post(url, {"order_id": order.id})
	assert res.status_code == status.HTTP_200_OK
	payment.refresh_from_db()
	assert payment.state == "FAILED"


@pytest.mark.django_db
def test_mark_payment_failed_already_failed(api_client):
	order = OrderFactory()
	payment = PaymentFactory(order=order, state="FAILED")
	url = reverse("mark-payment-failed")
	res = api_client.post(url, {"order_id": order.id})
	assert res.status_code == status.HTTP_200_OK
	assert res.json()["message"] == "Оплата уже помечена как FAILED"


@pytest.mark.django_db
def test_mark_payment_failed_already_paid(api_client):
	order = OrderFactory()
	PaymentFactory(order=order, state="PAID")
	url = reverse("mark-payment-failed")
	res = api_client.post(url, {"order_id": order.id})
	assert res.status_code == 400
	assert res.json()["error"] == "Оплата уже проведена (PAID), нельзя пометить как FAILED"


@pytest.mark.django_db
def test_mark_payment_failed_no_pending(api_client):
	order = OrderFactory()
	url = reverse("mark-payment-failed")
	res = api_client.post(url, {"order_id": order.id})
	assert res.status_code == 404
	assert res.json()["error"] == "Нет PENDING платежа"


@pytest.mark.django_db
def test_mark_payment_failed_order_not_found(api_client):
	url = reverse("mark-payment-failed")
	res = api_client.post(url, {"order_id": 999})
	assert res.status_code == 404
	assert res.json()["error"] == "Заказ не найден"


@pytest.mark.django_db
def test_order_status_success(auth_client):
	order = OrderFactory(state="NEW")
	url = reverse("order-status", args=[order.id])
	res = auth_client.get(url)
	assert res.status_code == status.HTTP_200_OK
	assert res.json()["state"] == "NEW"

@pytest.mark.django_db
def test_order_status_not_found(auth_client):
	url = reverse("order-status", args=[999])
	res = auth_client.get(url)
	assert res.status_code == status.HTTP_404_NOT_FOUND
	assert res.json()["error"] == "Заказ не найден"
