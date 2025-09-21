from django.urls import path
from .views import product_by_barcode, create_order, create_payment, order_status, mark_payment_paid, mark_payment_failed

urlpatterns = [
    path('product/<str:barcode>/', product_by_barcode, name='product-by-barcode'),
    path('order/create/', create_order, name='create-order'),
    path('order/status/<str:order_id>/', order_status, name='order-status'),
    path('payment/create/', create_payment, name='create-payment'),
    path('payment/mark_paid/', mark_payment_paid, name='mark-payment-paid'),
    path('payment/mark_failed/', mark_payment_failed, name='mark-payment-failed'),
]
