import logging
import requests
from celery import shared_task
from celery.exceptions import Retry
from django.db import transaction
from django.utils import timezone
from django.utils.formats import date_format
from django.db.models import Count, Sum
from pos.models import Order, Payment
from pos.flow import OrderFlow, PaymentFlow
from notifications.services import send_telegram

logger = logging.getLogger(__name__)

@shared_task(bind=True, name="archive_created_orders", max_retries=3, default_retry_delay=300)
def archive_created_orders(self):
    orders = Order.objects.filter(state=Order.OrderState.CREATED)
    logger.info(f"Found {orders.count()} orders to archive")

    for order in orders:
        try:
            with transaction.atomic():
                order = Order.objects.select_for_update().get(id=order.id)
                order_flow = OrderFlow(order)
                order_flow.archive()

                for payment in order.payments.all():
                    payment_flow = PaymentFlow(payment)
                    if payment.state == Payment.PaymentState.PENDING:
                        payment_flow.mark_failed()
                        logger.info(f"Payment {payment.id} marked as FAILED due to order archive")
        except Exception as e:
            logger.error(f"Failed to archive order {order.id}", exc_info=e)

@shared_task(bind=True, name="daily_orders_report", max_retries=3, default_retry_delay=300)
def daily_orders_report(self):
    today = timezone.localdate()
    today_str = date_format(today, format="j E Y", use_l10n=True)

    orders = Order.objects.filter(created_at__date=today)

    total_orders = orders.count()
    total_paid = orders.filter(state=Order.OrderState.PAID).count()
    total_cancelled = orders.filter(state=Order.OrderState.CANCELLED).count()
    total_archived = orders.filter(state=Order.OrderState.ARCHIEVE).count()
    total_revenue = orders.filter(state=Order.OrderState.PAID).aggregate(total=Sum("total_price"))["total"] or 0
    avg_check = round(total_revenue / total_paid, 2) if total_paid else 0
    cancel_pct = round((total_cancelled / total_orders) * 100, 1) if total_orders else 0

    # --- По POS ---
    pos_stats = []
    for pos_id, pos_orders in orders.values_list("pos_id", flat=True).distinct().iterator():
        pos_orders_qs = orders.filter(pos_id=pos_id)
        pos_name = pos_orders_qs.first().pos.name if pos_orders_qs.exists() else f"POS {pos_id}"
        pos_count = pos_orders_qs.count()
        pos_revenue = pos_orders_qs.filter(state=Order.OrderState.PAID).aggregate(total=Sum("total_price"))["total"] or 0
        pos_stats.append(f"{pos_name}: {pos_count} заказов, {pos_revenue} руб.")

    pos_lines = "\n".join(pos_stats) if pos_stats else "Нет заказов по POS"

    top_products = (
        OrderItem.objects.filter(order__created_at__date=today, order__state=Order.OrderState.PAID)
        .values("product__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:3]
    )
    top_lines = "\n".join([f"{i+1}. {p['product__name']} — {p['count']} шт." for i, p in enumerate(top_products)]) or "Нет продаж"

    message = (
        f"📊 Отчет за {today_str}:\n"
        f"Всего заказов: {total_orders}\n"
        f"Оплачено: {total_paid}\n"
        f"Отменено: {total_cancelled} ({cancel_pct}%)\n"
        f"Архивировано: {total_archived}\n"
        f"Выручка: {total_revenue} руб.\n"
        f"Средний чек: {avg_check} руб.\n\n"
        f"По POS:\n{pos_lines}\n\n"
        f"🔥 Топ-3 товара:\n{top_lines}"
    )

    logger.info(f"daily_orders_report: подготовлен отчет за {today_str}")
    try:
        send_telegram_message(message)
        logger.info("daily_orders_report: отчет успешно отправлен в Telegram")
    except requests.RequestException as exc:
        logger.exception("daily_orders_report: ошибка при отправке в Telegram")
        raise self.retry(exc=exc)
