from django.db import models
from simple_history.models import HistoricalRecords

class PointOfSale(models.Model):
    name = models.CharField("Название", max_length=255)
    location = models.CharField("Местоположение", max_length=255, blank=True)
    status = models.BooleanField("Активна", default=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Точка продаж"
        verbose_name_plural = "Точки продаж"

    def __str__(self):
        return self.name

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
    available = models.BooleanField("В наличии", default=True)
    description = models.TextField("Описание", blank=True)
    barcode = models.CharField("Штрихкод", max_length=100, unique=True, blank=True, null=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Товар/Блюдо"
        verbose_name_plural = "Товары/Блюда"

    def __str__(self):
        return self.name

class Order(models.Model):
    STATUS_CHOICES = [
        ("new", "Новый"),
        ("paid", "Оплачен"),
        ("cancelled", "Отменён"),
    ]
    pos = models.ForeignKey(PointOfSale, verbose_name="Точка продаж", on_delete=models.PROTECT, related_name="orders")
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default="new")
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)
    total_price = models.DecimalField("Итоговая сумма", max_digits=10, decimal_places=2, default=0)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"

    def __str__(self):
        return f"Заказ {self.id} на {self.pos}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, verbose_name="Заказ", on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, verbose_name="Продукт", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField("Количество", default=1)
    price = models.DecimalField("Цена на момент покупки", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

class Payment(models.Model):
    PAYMENT_CHOICES = [
        ("cash", "Наличные"),
        ("card", "Карта"),
    ]
    STATUS_CHOICES = [
        ("pending", "В ожидании"),
        ("paid", "Оплачен"),
        ("failed", "Неудача"),
    ]
    order = models.ForeignKey(Order, verbose_name="Заказ", on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField("Сумма", max_digits=10, decimal_places=2)
    payment_type = models.CharField("Тип оплаты", max_length=20, choices=PAYMENT_CHOICES)
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default="pending")
    processed_at = models.DateTimeField("Дата обработки", auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Оплата"
        verbose_name_plural = "Оплаты"

    def __str__(self):
        return f"{self.payment_type} {self.amount}"

class Receipt(models.Model):
    order = models.OneToOneField(Order, verbose_name="Заказ", on_delete=models.CASCADE, related_name="receipt")
    receipt_number = models.CharField("Номер чека", max_length=100, unique=True)
    fiscal_data = models.JSONField("Фискальные данные")
    issued_at = models.DateTimeField("Дата выдачи", auto_now_add=True)

    class Meta:
        verbose_name = "Фискальный чек"
        verbose_name_plural = "Фискальные чеки"

    def __str__(self):
        return f"Чек {self.receipt_number}"

class Stock(models.Model):
    pos = models.ForeignKey(PointOfSale, verbose_name="Точка продаж", on_delete=models.CASCADE, related_name="stocks")
    product = models.ForeignKey(Product, verbose_name="Товар", on_delete=models.CASCADE, related_name="stocks")
    quantity = models.PositiveIntegerField("Количество", default=0)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Остаток товара"
        verbose_name_plural = "Остатки товаров"
        unique_together = ("pos", "product")

    def __str__(self):
        return f"{self.product.name} на {self.pos.name}: {self.quantity}"
