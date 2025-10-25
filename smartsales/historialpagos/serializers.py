from rest_framework import serializers


class DetallePagoSerializer(serializers.Serializer):
    """Serializer para un producto en el detalle de la venta"""
    producto_id = serializers.IntegerField()
    producto_nombre = serializers.CharField()
    cantidad = serializers.IntegerField()
    precio_unitario = serializers.DecimalField(max_digits=12, decimal_places=2)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)


class HistorialPagoSerializer(serializers.Serializer):
    """Serializer para el historial de pagos del usuario"""
    pago_id = serializers.IntegerField()
    venta_id = serializers.IntegerField()
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    fecha_pago = serializers.DateTimeField()
    fecha_venta = serializers.DateTimeField()
    direccion_envio = serializers.CharField()
    productos = DetallePagoSerializer(many=True)
    
    # Campos opcionales de Stripe
    receipt_url = serializers.URLField(required=False, allow_null=True)
