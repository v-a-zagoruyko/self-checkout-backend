from rest_framework import serializers
from pos.models import Product, Stock, Order, OrderItem


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(read_only=True, slug_field="name")
    quantity = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "name", "weight", "category", "price", "barcode", "quantity"]

    def get_quantity(self, obj):
        pos = self.context.get("pos")
        if pos:
            stock = obj.stocks.filter(pos=pos).first()
            return stock.quantity if stock else 0
        return 0


class OrderItemCreateSerializer(serializers.Serializer):
    barcode = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):
    pos_code = serializers.CharField()
    order = OrderItemCreateSerializer(many=True)
