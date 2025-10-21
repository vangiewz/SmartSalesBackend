from rest_framework import serializers

class ProductoCreateSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=160)
    precio = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    tiempogarantia = serializers.IntegerField(min_value=0)
    stock = serializers.IntegerField(min_value=0)
    marca_id = serializers.IntegerField()
    tipoproducto_id = serializers.IntegerField()
    # La imagen se valida manualmente en la vista desde request.FILES

class ProductoUpdateSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=160, required=False)
    precio = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False)
    tiempogarantia = serializers.IntegerField(min_value=0, required=False)
    stock = serializers.IntegerField(min_value=0, required=False)
    marca_id = serializers.IntegerField(required=False)
    tipoproducto_id = serializers.IntegerField(required=False)
    # La imagen (opcional en update) se valida manualmente desde request.FILES

class ProductoQuerySerializer(serializers.Serializer):
    q = serializers.CharField(required=False, allow_blank=True)
    marca_id = serializers.IntegerField(required=False)
    tipoproducto_id = serializers.IntegerField(required=False)
    min_precio = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    max_precio = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    page = serializers.IntegerField(required=False, min_value=1)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100)
