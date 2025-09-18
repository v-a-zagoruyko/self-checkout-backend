from django.core.management.base import BaseCommand
from pos.models import PointOfSale, Category, Product, Stock, Order, OrderItem, Payment, Receipt
from simple_history.utils import update_change_reason
from decimal import Decimal
from faker import Faker
import random
import json

fake = Faker("ru_RU")

class Command(BaseCommand):
    help = "Реалистично заполняет базу тестовыми данными с датами в прошлом"

    def handle(self, *args, **kwargs):
        # Точки продаж
        pos_list = []
        for _ in range(3):
            pos = PointOfSale.objects.create(
                name=fake.company(),
                location=fake.address(),
                status=True
            )
            pos_list.append(pos)

        # Категории
        category_names = ["Напитки", "Блюда", "Десерты", "Снэки"]
        categories = [Category.objects.create(name=name) for name in category_names]

        # Продукты
        products = []
        for cat in categories:
            for _ in range(5):
                prod = Product.objects.create(
                    name=fake.word().capitalize(),
                    category=cat,
                    price=Decimal(random.randint(50, 500)),
                    available=random.choice([True, True, True, False]),
                    description=fake.sentence(),
                    barcode=fake.ean13()
                )
                products.append(prod)

        # Остатки (Stock)
        for pos in pos_list:
            for prod in products:
                Stock.objects.create(
                    pos=pos,
                    product=prod,
                    quantity=random.randint(10, 100)
                )

        # Заказы и позиции
        for _ in range(50):  # больше данных для аналитики
            order_pos = random.choice(pos_list)
            order_date = fake.date_time_between(start_date='-90d', end_date='now')
            order = Order.objects.create(
                pos=order_pos,
                status=random.choices(["new", "paid", "cancelled"], weights=[1, 3, 1])[0],
                total_price=0,
                created_at=order_date,
                updated_at=order_date
            )
            total = 0
            items = []
            for _ in range(random.randint(1, 5)):
                prod = random.choice(products)
                qty = random.randint(1, 5)
                item = OrderItem.objects.create(
                    order=order,
                    product=prod,
                    quantity=qty,
                    price=prod.price
                )
                items.append(item)
                total += prod.price * qty
            order.total_price = total
            order.save()

            # Оплата
            if order.status == "paid":
                Payment.objects.create(
                    order=order,
                    amount=total,
                    payment_type=random.choice(["cash", "card"]),
                    status="paid",
                    processed_at=order_date
                )
            elif order.status == "new":
                Payment.objects.create(
                    order=order,
                    amount=total,
                    payment_type=random.choice(["cash", "card"]),
                    status="pending",
                    processed_at=order_date
                )

            # Чек
            Receipt.objects.create(
                order=order,
                receipt_number=fake.unique.ean8(),
                fiscal_data=json.dumps([
                    {"name": item.product.name, "qty": item.quantity, "price": float(item.price)}
                    for item in items
                ]),
                issued_at=order_date
            )

        self.stdout.write(self.style.SUCCESS("Созданы реалистичные заказы с датами в прошлом"))
