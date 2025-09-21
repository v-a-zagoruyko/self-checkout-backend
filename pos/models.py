import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from simple_history.models import HistoricalRecords


class PointOfSale(models.Model):
    name = models.CharField("Название", max_length=255)
    code = models.CharField("Код точки", max_length=50, unique=True)
    location = models.CharField("Местоположение", max_length=255, blank=True)
    is_active = models.BooleanField("Активна", default=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Точка продаж"
        verbose_name_plural = "Точки продаж"

    def __str__(self):
        return self.name


class PointOfSaleToken(models.Model):
    pos = models.OneToOneField("PointOfSale", verbose_name="Точка продаж", on_delete=models.CASCADE, related_name="api_token")
    token = models.CharField("Токен", max_length=40, unique=True, default=uuid.uuid4())
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "POS-токен"
        verbose_name_plural = "POS-токены"

    def __str__(self):
        return f"{self.pos.name} token"


class Category(models.Model):
    name = models.CharField("Название категории", max_length=100)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField("Название", max_length=255)
    category = models.ForeignKey(Category, verbose_name="Категория", on_delete=models.PROTECT, related_name="products")
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2)
    description = models.TextField("Описание", blank=True)
    barcode = models.CharField("Штрихкод", max_length=100, unique=True, blank=True, null=True)
    weight = models.CharField("Вес/кол-во", max_length=50, blank=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

    def __str__(self):
        return self.name


class Stock(models.Model):
    pos = models.ForeignKey(PointOfSale, verbose_name="Точка продаж", on_delete=models.CASCADE, related_name="stocks")
    product = models.ForeignKey(Product, verbose_name="Товар", on_delete=models.CASCADE, related_name="stocks")
    quantity = models.IntegerField("Количество", default=0)
    is_active = models.BooleanField("Доступно к продаже", default=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Остаток"
        verbose_name_plural = "Остатки"
        unique_together = ("pos", "product")

    def __str__(self):
        return f"{self.product.name} на {self.pos.name}: {self.quantity}"


class Order(models.Model):
    class OrderState(models.TextChoices):
        CREATED = 'CREATED', 'Создан'
        PAID = 'PAID', 'Оплачен'
        CANCELLED = 'CANCELLED', 'Отменён'
        ARCHIEVE = 'ARCHIEVE', 'Архивирован'

    state = models.CharField("Статус", max_length=150, choices=OrderState.choices, default=OrderState.CREATED)
    pos = models.ForeignKey(PointOfSale, verbose_name="Точка продаж", on_delete=models.PROTECT, related_name="orders")
    total_price = models.DecimalField("Итоговая сумма", max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"

    def recalculate_total(self):
        total = sum(item.total_price for item in self.items.all())
        self.total_price = total
        self.save(update_fields=["total_price"])

    def __str__(self):
        return f"Заказ №{self.id} на {self.pos}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, verbose_name="Заказ", on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, verbose_name="Продукт", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField("Количество", default=1)
    price = models.DecimalField("Цена на момент покупки", max_digits=10, decimal_places=2)
    total_price = models.DecimalField("Общая цена", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.price
        super().save(*args, **kwargs)
        self.order.recalculate_total()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.order.recalculate_total()

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


class OrderComment(models.Model):
    order = models.ForeignKey(Order, verbose_name="Заказ", on_delete=models.CASCADE, related_name="comments")
    text = models.TextField("Комментарий")
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        verbose_name = "Комментарий к заказу"
        verbose_name_plural = "Комментарии к заказам"

    def __str__(self):
        return f"Комментарий к заказу №{self.order.id}"


class Payment(models.Model):
    class PaymentState(models.TextChoices):
        PENDING = "PENDING", "В ожидании"
        PAID = "PAID", "Оплачен"
        FAILED = "FAILED", "Неудача"

    PAYMENT_METHODS = [
        ("card", "Карта"),
        ("sbp", "СБП"),
    ]

    order = models.ForeignKey("Order", verbose_name="Заказ", on_delete=models.CASCADE, related_name="payments")
    state = models.CharField("Статус", max_length=20, choices=PaymentState.choices, default=PaymentState.PENDING)
    type = models.CharField("Метод оплаты", max_length=20, choices=PAYMENT_METHODS)
    link = models.URLField("Ссылка на оплату (эквайринг)", blank=True, null=True)
    processed_at = models.DateTimeField("Дата обработки", auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Оплата"
        verbose_name_plural = "Оплаты"

    def __str__(self):
        return f"Оплата заказа №{self.order.id} ({self.get_state_display()})"


class Receipt(models.Model):
    payment = models.OneToOneField("Payment", verbose_name="Платёж", on_delete=models.CASCADE, related_name="receipt")
    receipt_number = models.CharField("Номер чека", max_length=100, unique=True)
    fiscal_data = models.JSONField("Фискальные данные")
    issued_at = models.DateTimeField("Дата выдачи", auto_now_add=True)
    link = models.URLField("Ссылка на чек", blank=True)

    class Meta:
        verbose_name = "Фискальный чек"
        verbose_name_plural = "Фискальные чеки"

    def __str__(self):
        return f"Чек {self.receipt_number}"
