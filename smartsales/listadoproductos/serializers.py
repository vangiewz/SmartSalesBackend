from rest_framework import serializers

class ProductoListadoQuerySerializer(serializers.Serializer):
    """Serializer para filtros y búsqueda en el listado de productos"""
    q = serializers.CharField(required=False, allow_blank=True, help_text="Búsqueda por nombre de producto")
    marca_id = serializers.IntegerField(required=False, help_text="Filtrar por ID de marca")
    tipoproducto_id = serializers.IntegerField(required=False, help_text="Filtrar por ID de tipo de producto")
    min_precio = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, help_text="Precio mínimo")
    max_precio = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, help_text="Precio máximo")
    min_stock = serializers.IntegerField(required=False, help_text="Stock mínimo")
    max_stock = serializers.IntegerField(required=False, help_text="Stock máximo")
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100, default=20)
