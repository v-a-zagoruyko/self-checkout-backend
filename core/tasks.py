import logging
from celery import shared_task
from django.db import transaction
from pos.models import Order, Payment
from pos.flow import OrderFlow, PaymentFlow

logger = logging.getLogger(__name__)

@shared_task(bind=True, name="archive_created_orders")
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
