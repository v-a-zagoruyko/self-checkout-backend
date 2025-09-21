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
from core.utils.notifications import send_telegram_message
from core.utils.reports import build_daily_report

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
    data = build_daily_report()
    today_str = data["date"]

    message = (
        f"📊 Отчет за {data['date']}:\n"
        f"Всего заказов: {data['total_orders']}\n"
        f"Оплачено: {data['total_paid']}\n"
        f"Отменено: {data['total_cancelled']} ({data['cancel_pct']}%)\n"
        f"Архивировано: {data['total_archived']}\n"
        f"Выручка: {data['total_revenue']} руб.\n"
        f"Средний чек: {data['avg_check']} руб.\n\n"
        f"По POS:\n{data['pos_lines']}\n\n"
        f"🔥 Топ-3 товара:\n{data['top_lines']}"
    )

    logger.info(f"daily_orders_report: подготовлен отчет за {today_str}")
    try:
        send_telegram_message(message)
        logger.info("daily_orders_report: отчет успешно отправлен в Telegram")
    except requests.RequestException as exc:
        logger.exception("daily_orders_report: ошибка при отправке в Telegram")
        raise self.retry(exc=exc)