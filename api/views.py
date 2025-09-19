from django.db import transaction
from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from pos.models import Product, PointOfSale, Stock, Order, OrderItem, Payment, Receipt
from pos.flow import OrderFlow, PaymentFlow
from .serializers import ProductSerializer, OrderCreateSerializer

from decimal import Decimal
import uuid

def send_to_acquiring(payment: Payment):
    return f"https://fake-acquiring.com/pay/{uuid.uuid4()}"

@api_view(['GET'])
def product_by_barcode(request, barcode):
    pos_code = request.GET.get("pos_code")

    if not pos_code:
        return Response({"error": "Не указан код точки продаж"}, status=400)

    try:
        pos = PointOfSale.objects.get(code=pos_code)
    except PointOfSale.DoesNotExist:
        return Response({"error": "Точка продаж не найдена"}, status=404)

    stock = Stock.objects.filter(pos=pos, product__barcode=barcode).first()
    if not stock or not stock.available_for_sale:
        return Response({"error": "Товар не найден или недоступен"}, status=404)

    serializer = ProductSerializer(stock.product, context={"pos": pos})
    return Response(serializer.data)

@api_view(['POST'])
def create_order(request):
    serializer = OrderCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    pos_code = serializer.validated_data['pos_code']
    order_items_data = serializer.validated_data['order']

    try:
        pos = PointOfSale.objects.get(code=pos_code)
    except PointOfSale.DoesNotExist:
        return Response({"error": "Точка продаж не найдена"}, status=404)

    try:
        with transaction.atomic():
            order = Order.objects.create(pos=pos)

            total = 0
            for item_data in order_items_data:
                try:
                    product = Product.objects.get(barcode=item_data['barcode'])
                except Product.DoesNotExist:
                    raise serializers.ValidationError(
                        f"Продукт с штрихкодом {item_data['barcode']} не найден"
                    )

                order_item = OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item_data['quantity'],
                    price=product.price
                )
                total += order_item.total_price

            order.total_price = total
            order.save()

    except serializers.ValidationError as e:
        return Response({"error": str(e)}, status=404)

    return Response({"order_id": order.id, "total_price": order.total_price})

@api_view(['POST'])
def create_payment(request):
    order_id = request.data.get("order_id")
    payment_type = request.data.get("payment_type")

    if not order_id or not payment_type:
        return Response({"error": "order_id и payment_type обязательны"}, status=400)

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({"error": "Заказ не найден"}, status=404)

    payment = order.payments.filter(state=Payment.PaymentState.PENDING).first()
    if not payment:
        payment = Payment.objects.create(
            order=order,
            state=Payment.PaymentState.PENDING,
            payment_type=payment_type
        )
        payment.payment_url = send_to_acquiring(payment)
        payment.save()

    return Response({"payment_id": payment.id, "payment_url": payment.payment_url})


@api_view(['GET'])
def order_status(request, order_id):
    if not order_id:
        return Response({"error": "order_id обязателен"}, status=400)

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({"error": "Заказ не найден"}, status=404)

    return Response({"state": order.state})


@api_view(['POST'])
def mark_payment_paid(request):
    order_id = request.data.get("order_id")
    if not order_id:
        return Response({"error": "order_id обязателен"}, status=400)

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({"error": "Заказ не найден"}, status=404)

    payment = order.payments.filter(state=Payment.PaymentState.PENDING).first()
    if not payment:
        return Response({"error": "Нет PENDING платежа"}, status=404)

    # TODO: разрулить транзакции
    order_flow = OrderFlow(order)
    order_flow.mark_paid()
    payment_flow = PaymentFlow(payment)
    payment_flow.mark_paid()
    Receipt.objects.create(
        payment=payment,
        receipt_number=str(uuid.uuid4()),
        fiscal_data=[{"name": item.product.name, "qty": item.quantity, "price": float(item.price)} for item in order.items.all()]
    )

    return Response({"message": "Оплата помечена как PAID"})

@api_view(['POST'])
def mark_payment_failed(request):
    order_id = request.data.get("order_id")
    if not order_id:
        return Response({"error": "order_id обязателен"}, status=400)

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({"error": "Заказ не найден"}, status=404)

    payment = order.payments.filter(state=Payment.PaymentState.PENDING).first()
    if not payment:
        return Response({"error": "Нет PENDING платежа"}, status=404)

    # TODO: разрулить транзакции
    order_flow = OrderFlow(order)
    order_flow.mark_cancelled()
    payment_flow = PaymentFlow(payment)
    payment_flow.mark_failed()

    return Response({"message": "Оплата помечена как FAILED"})
