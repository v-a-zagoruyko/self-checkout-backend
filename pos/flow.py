import logging
from django.utils import timezone
from viewflow import fsm
from .models import Order, Payment

logger = logging.getLogger(__name__)


class OrderFlow:
    state = fsm.State(Order.OrderState, default=Order.OrderState.CREATED)

    def __init__(self, order):
        self.order = order

    @state.setter()
    def _set_state(self, value):
        self.order.state = value

    @state.getter()
    def _get_state(self):
        return getattr(self.order, "state", Order.OrderState.CREATED)

    @state.transition(source=Order.OrderState.CREATED, target=Order.OrderState.PAID)
    def mark_paid(self):
        logger.info(f"Order {self.order.id} marked as PAID")

    @state.transition(source=[Order.OrderState.CREATED, Order.OrderState.PAID], target=Order.OrderState.CANCELLED)
    def mark_cancelled(self):
        logger.info(f"Order {self.order.id} marked as CANCELLED")

    @state.transition(source=[Order.OrderState.CREATED], target=Order.OrderState.ARCHIEVE)
    def archive(self):
        logger.info(f"Order {self.order.id} moved to ARCHIEVE")

    @state.on_success()
    def _on_success(self, descriptor, source, target):
        self.order.save()


class PaymentFlow:
    state = fsm.State(Payment.PaymentState, default=Payment.PaymentState.PENDING)

    def __init__(self, payment):
        self.payment = payment

    @state.setter()
    def _set_state(self, value):
        self.payment.state = value

    @state.getter()
    def _get_state(self):
        return getattr(self.payment, "state", Payment.PaymentState.PENDING)

    @state.transition(source=Payment.PaymentState.PENDING, target=Payment.PaymentState.PAID)
    def mark_paid(self):
        logger.info(f"Payment {self.payment.id} marked as PAID")

    @state.transition(source=Payment.PaymentState.PENDING, target=Payment.PaymentState.FAILED)
    def mark_failed(self):
        logger.info(f"Payment {self.payment.id} marked as FAILED")

    @state.on_success()
    def _on_success(self, descriptor, source, target):
        if target in [Payment.PaymentState.PAID, Payment.PaymentState.FAILED]:
            self.payment.processed_at = timezone.now()
        self.payment.save()
