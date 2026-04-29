from rest_framework import serializers


class SupplierAlertSerializer(serializers.Serializer):
    id            = serializers.IntegerField()
    name          = serializers.CharField()
    contact_email = serializers.EmailField(allow_null=True)


class LowStockAlertSerializer(serializers.Serializer):
    product_id          = serializers.IntegerField()
    product_name        = serializers.CharField()
    sku                 = serializers.CharField()
    warehouse_id        = serializers.IntegerField()
    warehouse_name      = serializers.CharField()
    current_stock       = serializers.IntegerField()
    threshold           = serializers.IntegerField()
    days_until_stockout = serializers.IntegerField(allow_null=True)
    supplier            = SupplierAlertSerializer(allow_null=True)


class LowStockResponseSerializer(serializers.Serializer):
    alerts       = LowStockAlertSerializer(many=True)
    total_alerts = serializers.IntegerField()