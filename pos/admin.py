from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import PointOfSale, Category, Product, Order, OrderItem, Payment, Receipt, Stock

@admin.register(PointOfSale)
class PointOfSaleAdmin(SimpleHistoryAdmin):
    list_display = ("name", "location", "status", "created_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("name", "location")

@admin.register(Category)
class CategoryAdmin(SimpleHistoryAdmin):
    list_display = ("name",)
    search_fields = ("name",)

@admin.register(Product)
class ProductAdmin(SimpleHistoryAdmin):
    list_display = ("name", "category", "price", "available", "barcode")
    list_filter = ("category", "available")
    search_fields = ("name", "barcode")

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("price",)
    autocomplete_fields = ("product",)

@admin.register(Order)
class OrderAdmin(SimpleHistoryAdmin):
    list_display = ("id", "pos", "status", "total_price", "created_at", "updated_at")
    list_filter = ("status", "pos")
    search_fields = ("id",)
    inlines = [OrderItemInline]

@admin.register(Payment)
class PaymentAdmin(SimpleHistoryAdmin):
    list_display = ("order", "payment_type", "amount", "status", "processed_at")
    list_filter = ("payment_type", "status")
    search_fields = ("order__id",)

@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ("receipt_number", "order", "issued_at")
    search_fields = ("receipt_number", "order__id")

@admin.register(Stock)
class StockAdmin(SimpleHistoryAdmin):
    list_display = ("pos", "product", "quantity")
    list_filter = ("pos", "product")
    search_fields = ("pos__name", "product__name")
