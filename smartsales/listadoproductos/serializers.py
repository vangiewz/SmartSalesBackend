# smartsales/listadoproductos/serializers.py
import os
from rest_framework import serializers
from smartsales.ventas_historicas.models import Producto, Marca, TipoProducto


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


class MarcaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marca
        fields = ["id", "nombre"]


class TipoProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoProducto
        fields = ["id", "nombre"]


class ProductoCatalogoSerializer(serializers.ModelSerializer):
    marca = MarcaSerializer(read_only=True)
    tipoproducto = TipoProductoSerializer(read_only=True)
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            "id",
            "nombre",
            "precio",
            "stock",
            "marca",
            "tipoproducto",
            "imagen_key",   # 👈 también mandamos la key
            "imagen_url",   # 👈 URL completa construida aquí
        ]

    def get_imagen_url(self, obj):
        """
        Construye la URL pública a partir de imagen_key usando SUPABASE_URL
        para que el frontend no tenga que conocer Supabase.
        """
        key = getattr(obj, "imagen_key", None)
        if not key:
            return None

        base_url = os.getenv("SUPABASE_URL")  # el mismo que usas en tus scripts Python

        if not base_url:
            # Si por algún motivo no está configurado, devolvemos la key cruda
            # (el frontend igual puede intentar usarla)
            return key

        # Ej: https://TU-PROYECTO.supabase.co/storage/v1/object/public/productos/uuid/14.jpeg
        return f"{base_url}/storage/v1/object/public/productos/{key}"
