from django.contrib import admin
from django.http import HttpResponseRedirect
from .flow import OrderFlow, PaymentFlow
from .models import (
    PointOfSale, Category, Product, Stock,
    Order, OrderItem, OrderComment,
    Payment, Receipt
)
from simple_history.admin import SimpleHistoryAdmin

admin.site.site_header = "Администрирование"
admin.site.site_title = "Администрирование"
admin.site.index_title = "Панель управления"
admin.site.site_url = None


@admin.register(PointOfSale)
class PointOfSaleAdmin(SimpleHistoryAdmin):
    list_display = ["name", "code", "location", "status", "created_at", "updated_at"]
    readonly_fields = ["created_at", "updated_at"]
    search_fields = ["name", "code"]
    list_filter = ["status"]


@admin.register(Category)
class CategoryAdmin(SimpleHistoryAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(Product)
class ProductAdmin(SimpleHistoryAdmin):
    list_display = ["name", "category", "price", "barcode", "weight"]
    list_filter = ["category"]
    search_fields = ["name", "barcode"]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Stock)
class StockAdmin(SimpleHistoryAdmin):
    list_display = ["product", "pos", "quantity", "available_for_sale"]
    list_filter = ["pos", "available_for_sale"]
    search_fields = ["product__name", "pos__name"]

    def has_delete_permission(self, request, obj=None):
        return False


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ["product", "quantity", "price", "total_price"]
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class OrderCommentInline(admin.TabularInline):
    model = OrderComment
    readonly_fields = ["created_at", "order"]
    extra = 0
    can_delete = False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    readonly_fields = ["state", "pos", "total_price", "created_at", "updated_at"]
    list_display = ["id", "pos", "state", "total_price", "created_at",]
    list_display_links = ["id", "pos"]
    list_filter = ["state", "pos"]
    search_fields = ["id", "pos__name"]
    inlines = [OrderItemInline, OrderCommentInline]

    def change_view(self, request, object_id, form_url='', extra_context=None):
        if '_archive' in request.POST:
            order = self.get_object(request, object_id)
            order_flow = OrderFlow(order)
            order_flow.archive()
            self.message_user(request, "Заказ отправлен в архив!")
            return HttpResponseRedirect(request.path)
        return super().change_view(request, object_id, form_url, extra_context)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "payment_type", "state", "processed_at"]
    list_display_links = ["id", "order"]
    list_filter = ["state", "payment_type"]
    search_fields = ["order__id"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Receipt)
class ReceiptAdmin(SimpleHistoryAdmin):
    list_display = ["payment", "receipt_number", "issued_at", "link"]
    readonly_fields = ["issued_at"]
    search_fields = ["receipt_number", "order__id"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
