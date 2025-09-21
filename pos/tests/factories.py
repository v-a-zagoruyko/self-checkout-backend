import uuid
import factory
from decimal import Decimal
from django.utils import timezone
from pos.models import Order, OrderItem, Payment, Category, Product, Stock, PointOfSale, PointOfSaleToken


class PointOfSaleFactory(factory.django.DjangoModelFactory):
	class Meta:
		model = PointOfSale
	name = factory.Sequence(lambda n: f"POS {n}")
	code = factory.Sequence(lambda n: str(uuid.uuid4()))


class PointOfSaleTokenFactory(factory.django.DjangoModelFactory):
	class Meta:
		model = PointOfSaleToken

	pos = factory.SubFactory(PointOfSaleFactory)
	token = factory.Sequence(lambda n: str(uuid.uuid4()))


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Category {n}")


class ProductFactory(factory.django.DjangoModelFactory):
	class Meta:
		model = Product
	name = factory.Sequence(lambda n: f"Product {n}")
	price = Decimal('100.00')
	category = factory.SubFactory(CategoryFactory)
	description = "Some description"
	barcode = factory.Sequence(lambda n: f"barcode-{n}")
	weight = "1 kg"


class StockFactory(factory.django.DjangoModelFactory):
	class Meta:
		model = Stock
	product = factory.SubFactory(ProductFactory)
	pos = factory.SubFactory(PointOfSaleFactory)
	quantity = 10
	is_active = True


class OrderFactory(factory.django.DjangoModelFactory):
	class Meta:
		model = Order
	pos = factory.SubFactory(PointOfSaleFactory)
	state = Order.OrderState.CREATED
	created_at = factory.LazyFunction(timezone.now)


class OrderItemFactory(factory.django.DjangoModelFactory):
	class Meta:
		model = OrderItem
	order = factory.SubFactory(OrderFactory)
	product = factory.SubFactory(ProductFactory)
	quantity = 1
	price = 100
	total_price = 100


class PaymentFactory(factory.django.DjangoModelFactory):
	class Meta:
		model = Payment

	order = factory.SubFactory(OrderFactory)
	type = "card"
	state = Payment.PaymentState.PENDING
	link = factory.LazyAttribute(lambda o: f"https://pay.test/{o.order.id}/{o.type}")
