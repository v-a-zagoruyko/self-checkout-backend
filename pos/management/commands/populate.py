from django.core.management.base import BaseCommand
from pos.models import PointOfSale, Category, Product, Stock, Order, OrderItem, Payment, Receipt
from decimal import Decimal
from faker import Faker
import random
import json
from datetime import timedelta, datetime

fake = Faker("ru_RU")

class Command(BaseCommand):
    help = "Реалистично заполняет базу тестовыми данными с датами в прошлом"

    def handle(self, *args, **kwargs):
        # --- Создание точек продаж ---
        pos_list = []
        for _ in range(3):
            pos = PointOfSale.objects.create(
                name=fake.company(),
                code=fake.unique.bothify(text="POS###???"),
                location=fake.address(),
                status=True
            )
            pos_list.append(pos)

        # --- Создание категорий ---
        category_names = ["Напитки", "Блюда", "Десерты", "Снэки"]
        categories = [Category.objects.create(name=name) for name in category_names]

        # --- Создание продуктов ---
        products = []
        for cat in categories:
            for _ in range(5):
                prod = Product.objects.create(
                    name=fake.word().capitalize(),
                    category=cat,
                    price=Decimal(random.randint(50, 500)),
                    description=fake.sentence(),
                    barcode=fake.unique.ean13(),
                    weight=f"{random.randint(50,500)}г"
                )
                products.append(prod)

        # --- Заполнение остатков на складах (Stock) ---
        for pos in pos_list:
            for prod in products:
                Stock.objects.create(
                    pos=pos,
                    product=prod,
                    quantity=random.randint(10, 100),
                    available_for_sale=random.choice([True, True, True, False])
                )

        # --- Создание заказов ---
        for _ in range(50):
            order_pos = random.choice(pos_list)
            order_date = fake.date_time_between(start_date='-90d', end_date='now')

            order_state = random.choices(
                [Order.OrderState.CREATED, Order.OrderState.PAID, Order.OrderState.CANCELLED],
                weights=[1,3,1]
            )[0]

            order = Order.objects.create(
                pos=order_pos,
                state=order_state,
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
                total += item.total_price

            order.total_price = total
            order.save()

            # --- Создание одного Payment на заказ ---
            if order.state == Order.OrderState.PAID:
                payment_state = Payment.PaymentState.PAID
            elif order.state == Order.OrderState.CREATED:
                payment_state = Payment.PaymentState.PENDING
            else:  # CANCELLED
                payment_state = Payment.PaymentState.FAILED

            payment = Payment.objects.create(
                order=order,
                state=payment_state,
                payment_type=random.choice(["card", "sbp"]),
                processed_at=order_date
            )

            # --- Создание чека ---
            Receipt.objects.create(
                payment=payment,
                receipt_number=fake.unique.ean8(),
                fiscal_data=json.dumps([
                    {"name": item.product.name, "qty": item.quantity, "price": float(item.price)}
                    for item in items
                ]),
                issued_at=order_date
            )

        self.stdout.write(self.style.SUCCESS("База данных успешно заполнена реалистичными заказами"))
