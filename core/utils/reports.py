from django.db.models import Sum, Count
from django.utils import timezone
from django.utils.formats import date_format
from pos.models import Order, OrderItem

def build_daily_report(date=None):
	today = date or timezone.localdate()
	today_str = date_format(today, format="j E Y", use_l10n=True)

	orders = Order.objects.filter(created_at__date=today)

	total_orders = orders.count()
	total_paid = orders.filter(state=Order.OrderState.PAID).count()
	total_cancelled = orders.filter(state=Order.OrderState.CANCELLED).count()
	total_archived = orders.filter(state=Order.OrderState.ARCHIEVE).count()
	total_revenue = orders.filter(state=Order.OrderState.PAID).aggregate(total=Sum("total_price"))["total"] or 0
	avg_check = round(total_revenue / total_paid, 2) if total_paid else 0
	cancel_pct = round((total_cancelled / total_orders) * 100, 1) if total_orders else 0

	pos_stats = []
	for pos_id in orders.values_list("pos_id", flat=True).distinct():
		pos_orders_qs = orders.filter(pos_id=pos_id)
		pos_name = pos_orders_qs.first().pos.name if pos_orders_qs.exists() else f"POS {pos_id}"
		pos_count = pos_orders_qs.count()
		pos_revenue = pos_orders_qs.filter(state=Order.OrderState.PAID).aggregate(total=Sum("total_price"))["total"] or 0
		pos_stats.append({"pos_id": pos_id, "pos_name": pos_name, "count": pos_count, "revenue": pos_revenue})

	pos_lines = "\n".join([f"{s['pos_name']}: {s['count']} заказов, {s['revenue']} руб." for s in pos_stats]) if pos_stats else "Нет заказов по POS"

	top_products = (
		OrderItem.objects.filter(order__created_at__date=today, order__state=Order.OrderState.PAID)
		.values("product__name")
		.annotate(count=Count("id"))
		.order_by("-count")[:3]
	)
	top_lines = "\n".join([f"{i+1}. {p['product__name']} — {p['count']} шт." for i, p in enumerate(top_products)]) or "Нет продаж"

	return {
		"date": today_str,
		"total_orders": total_orders,
		"total_paid": total_paid,
		"total_cancelled": total_cancelled,
		"total_archived": total_archived,
		"total_revenue": total_revenue,
		"avg_check": avg_check,
		"cancel_pct": cancel_pct,
		"pos_stats": pos_stats,
		"pos_lines": pos_lines,
		"top_lines": top_lines,
	}
