# smartsales/garantia/serializers.py
from rest_framework import serializers

class ClaimCreateSerializer(serializers.Serializer):
    venta_id = serializers.IntegerField()
    producto_id = serializers.IntegerField()
    cantidad = serializers.IntegerField(min_value=1)
    motivo = serializers.CharField(max_length=200)

class ClaimEvaluateSerializer(serializers.Serializer):
    # reemplazo: True => reemplazar; False => reparar; None/ausente => rechazar
    reemplazo = serializers.BooleanField(required=False, allow_null=True)
    evaluacion = serializers.ChoiceField(
        choices=["Reparar", "Reemplazar", "Rechazar"], 
        required=False
    )
    comentario_tecnico = serializers.CharField(max_length=500, required=False, allow_blank=True)

class ClaimListQuerySerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=["Pendiente", "Completado", "Rechazado"], required=False)
    venta_id = serializers.IntegerField(required=False)
    producto_id = serializers.IntegerField(required=False)
    desde = serializers.DateTimeField(required=False)
    hasta = serializers.DateTimeField(required=False)
    q = serializers.CharField(required=False, allow_blank=True)         # búsqueda por nombre de producto
    cliente = serializers.CharField(required=False, allow_blank=True)   # solo en scope global
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100, default=20)

class ClaimResponseSerializer(serializers.Serializer):
    venta_id = serializers.IntegerField()
    producto_id = serializers.IntegerField()
    garantia_id = serializers.IntegerField()
    estado = serializers.CharField()
    cantidad = serializers.IntegerField()
    motivo = serializers.CharField()
    hora = serializers.DateTimeField(allow_null=True)
    reemplazo = serializers.BooleanField(allow_null=True)
    producto_nombre = serializers.CharField()
    producto_imagen_url = serializers.CharField(allow_blank=True)
    limitegarantia = serializers.DateTimeField(allow_null=True)

class ClaimDetailResponseSerializer(serializers.Serializer):
    garantia_id = serializers.IntegerField()
    venta_id = serializers.IntegerField()
    producto_id = serializers.IntegerField()
    producto_nombre = serializers.CharField()
    producto_imagen_url = serializers.CharField(allow_blank=True)
    producto_descripcion = serializers.CharField(allow_blank=True)
    producto_garantia_dias = serializers.IntegerField()
    fecha_venta = serializers.DateTimeField()
    fecha_solicitud = serializers.DateTimeField(allow_null=True)
    limite_garantia = serializers.DateTimeField()
    estado = serializers.CharField()
    motivo = serializers.CharField()
    cantidad = serializers.IntegerField()
    evaluacion = serializers.CharField(allow_null=True)
    comentario_tecnico = serializers.CharField(allow_blank=True, allow_null=True)
    fecha_evaluacion = serializers.DateTimeField(allow_null=True)
    tecnico_id = serializers.CharField(allow_null=True)
    tecnico_nombre = serializers.CharField(allow_blank=True, allow_null=True)
    es_reemplazo = serializers.BooleanField(allow_null=True)
    cliente_nombre = serializers.CharField()
    cliente_email = serializers.CharField()
    cliente_telefono = serializers.CharField(allow_blank=True, allow_null=True)

