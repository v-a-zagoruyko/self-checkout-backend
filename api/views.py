import logging
import uuid
from django.db import transaction
from rest_framework import serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.auth import POSTokenAuthentication
from pos.models import Product, PointOfSale, Stock, Order, OrderItem, Payment, Receipt
from pos.flow import OrderFlow, PaymentFlow
from .serializers import ProductSerializer, OrderCreateSerializer

logger = logging.getLogger(__name__)

def send_to_acquiring(payment: Payment):
    return f"https://fake-acquiring.com/pay/{uuid.uuid4()}"


@api_view(['GET'])
@authentication_classes([SessionAuthentication, POSTokenAuthentication])
@permission_classes([IsAuthenticated])
def product_by_barcode(request, barcode):
    pos_code = request.GET.get("pos_code")

    if not pos_code:
        return Response({"error": "Не указан код точки продаж"}, status=400)

    try:
        pos = PointOfSale.objects.get(code=pos_code)
    except PointOfSale.DoesNotExist:
        return Response({"error": "Точка продаж не найдена"}, status=404)

    stock = Stock.objects.filter(pos=pos, product__barcode=barcode).first()
    if not stock or not stock.is_active:
        return Response({"error": "Товар не найден или недоступен"}, status=404)

    serializer = ProductSerializer(stock.product, context={"pos": pos})
    return Response(serializer.data)


@api_view(['POST'])
@authentication_classes([SessionAuthentication, POSTokenAuthentication])
@permission_classes([IsAuthenticated])
def create_order(request):
    serializer = OrderCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    pos_code = serializer.validated_data['pos_code']
    order_items_data = serializer.validated_data['order']

    try:
        pos = PointOfSale.objects.get(code=pos_code)
    except PointOfSale.DoesNotExist:
        logger.warning("POS not found", extra={"pos_code": pos_code})
        return Response({"error": "Точка продаж не найдена"}, status=404)

    try:
        with transaction.atomic():
            order = Order.objects.create(pos=pos)
            for item_data in order_items_data:
                product = Product.objects.select_for_update().filter(barcode=item_data['barcode']).first()
                if not product:
                    logger.warning(f"Продукт с штрихкодом {item_data['barcode']} не найден")
                    raise serializers.ValidationError(f"Продукт с штрихкодом {item_data['barcode']} не найден")
                stock = Stock.objects.select_for_update().filter(pos=pos, product=product).first()
                if not stock or stock.quantity < item_data['quantity'] or not stock.is_active:
                    logger.warning(f"Заказ №{order.id}, Недостаточно товара {product.name}")
                order_item = OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item_data['quantity'],
                    price=product.price
                )
                stock.quantity -= item_data['quantity']
                stock.save()
            order.save()
    except serializers.ValidationError as e:
        logger.info("Create order validation failed", extra={"error": str(e)})
        return Response({"error": str(e)}, status=400)

    logger.info("Order created", extra={"order_id": order.id, "total": str(order.total_price)})
    return Response({"order_id": order.id, "total_price": order.total_price})


@api_view(['POST'])
@authentication_classes([SessionAuthentication, POSTokenAuthentication])
@permission_classes([IsAuthenticated])
def create_payment(request):
    order_id = request.data.get("order_id")
    payment_type = request.data.get("payment_type")

    if payment_type not in dict(Payment.PAYMENT_METHODS):
        return Response({"error": "Неправильный payment_type"}, status=400)

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({"error": "Order not found"}, status=404)

    if order.payments.filter(state=Payment.PaymentState.PAID).exists():
        return Response({"error": "Order already has a PAID payment"}, status=400)

    existing_payment = order.payments.filter(type=payment_type).first()
    if existing_payment:
        return Response({
            "payment_id": existing_payment.id,
            "payment_link": existing_payment.link
        })

    payment = Payment.objects.create(order=order, type=payment_type, link=send_to_acquiring(payment_type))

    return Response({
        "payment_id": payment.id,
        "payment_link": payment.link
    })


@api_view(['GET'])
@authentication_classes([SessionAuthentication, POSTokenAuthentication])
@permission_classes([IsAuthenticated])
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
        with transaction.atomic():
            order = Order.objects.select_for_update().get(id=order_id)
            payment = order.payments.select_for_update().filter(state=Payment.PaymentState.PENDING).first()
            if not payment:
                existing = order.payments.filter(state=Payment.PaymentState.PAID).first()
                if existing:
                    logger.info("Payment already paid", extra={"order_id": order.id, "payment_id": existing.id})
                    return Response({"message": "Оплата уже помечена как PAID"})
                return Response({"error": "Нет PENDING платежа"}, status=404)
            order_flow = OrderFlow(order)
            order_flow.mark_paid()
            payment_flow = PaymentFlow(payment)
            payment_flow.mark_paid()
            Receipt.objects.create(
                payment=payment,
                receipt_number=str(uuid.uuid4()),
                fiscal_data=[{"name": item.product.name, "qty": item.quantity, "price": float(item.price)} for item in order.items.all()]
            )
    except Order.DoesNotExist:
        return Response({"error": "Заказ не найден"}, status=404)

    logger.info("Payment marked paid", extra={"order_id": order.id, "payment_id": payment.id})
    return Response({"message": "Оплата помечена как PAID"})


@api_view(['POST'])
def mark_payment_failed(request):
    order_id = request.data.get("order_id")
    if not order_id:
        return Response({"error": "order_id обязателен"}, status=400)

    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(id=order_id)
            payment = order.payments.select_for_update().filter(state=Payment.PaymentState.PENDING).first()
            if not payment:
                existing_failed = order.payments.filter(state=Payment.PaymentState.FAILED).first()
                if existing_failed:
                    logger.info("Payment already failed", extra={"order_id": order.id, "payment_id": existing_failed.id})
                    return Response({"message": "Оплата уже помечена как FAILED"})
                existing_paid = order.payments.filter(state=Payment.PaymentState.PAID).first()
                if existing_paid:
                    logger.warning("Tried to mark payment failed, but already paid", extra={"order_id": order.id, "payment_id": existing_paid.id})
                    return Response({"error": "Оплата уже проведена (PAID), нельзя пометить как FAILED"}, status=400)
                return Response({"error": "Нет PENDING платежа"}, status=404)

            order_flow = OrderFlow(order)
            order_flow.mark_cancelled()
            payment_flow = PaymentFlow(payment)
            payment_flow.mark_failed()
    except Order.DoesNotExist:
        return Response({"error": "Заказ не найден"}, status=404)

    logger.info("Payment marked failed", extra={"order_id": order.id, "payment_id": payment.id})
    return Response({"message": "Оплата помечена как FAILED"})
