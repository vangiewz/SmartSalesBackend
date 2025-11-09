# smartsales/carrito_voz/serializers.py

from decimal import Decimal
from typing import List

from rest_framework import serializers


class CarritoVozRequestSerializer(serializers.Serializer):
    usuario_id = serializers.UUIDField()
    texto = serializers.CharField(
        help_text="Texto transcrito de la orden por voz (en español)."
    )
    limite_items = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=50,
        default=10,
        help_text="Número máximo de ítems sugeridos en el carrito.",
    )


class ProductoOpcionSerializer(serializers.Serializer):
    producto_id = serializers.IntegerField()
    nombre = serializers.CharField()
    precio_unitario = serializers.DecimalField(max_digits=12, decimal_places=2)


class CarritoVozItemSerializer(serializers.Serializer):
    producto_id = serializers.IntegerField()
    nombre = serializers.CharField()
    cantidad = serializers.IntegerField(min_value=1)
    precio_unitario = serializers.DecimalField(max_digits=12, decimal_places=2)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)
    fragmento_voz = serializers.CharField()
    # nuevas opciones sugeridas para el mismo fragmento de voz
    opciones = ProductoOpcionSerializer(many=True, required=False)


class CarritoVozResponseSerializer(serializers.Serializer):
    usuario_id = serializers.UUIDField()
    texto = serializers.CharField()
    total_estimado = serializers.DecimalField(max_digits=12, decimal_places=2)
    items = CarritoVozItemSerializer(many=True)
    fragmentos_sin_match = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    mensaje = serializers.CharField(required=False)

    def to_representation(self, instance):
        """
        Asegura que los Decimals se serialicen correctamente si vienen de servicios.
        """
        data = super().to_representation(instance)

        # Si total_estimado viene como Decimal, lo convertimos de forma segura
        total = instance.get("total_estimado")
        if isinstance(total, Decimal):
            data["total_estimado"] = f"{total:.2f}"

        # Items
        items: List[dict] = instance.get("items", [])
        data_items = []
        for item in items:
            item_data = {
                "producto_id": item["producto_id"],
                "nombre": item["nombre"],
                "cantidad": item["cantidad"],
                "precio_unitario": f"{item['precio_unitario']:.2f}"
                if isinstance(item["precio_unitario"], Decimal)
                else item["precio_unitario"],
                "subtotal": f"{item['subtotal']:.2f}"
                if isinstance(item["subtotal"], Decimal)
                else item["subtotal"],
                "fragmento_voz": item["fragmento_voz"],
            }

            # Opciones alternativas, si existen
            opciones = item.get("opciones", [])
            data_opciones = []
            for opt in opciones:
                opt_data = {
                    "producto_id": opt["producto_id"],
                    "nombre": opt["nombre"],
                    "precio_unitario": f"{opt['precio_unitario']:.2f}"
                    if isinstance(opt["precio_unitario"], Decimal)
                    else opt["precio_unitario"],
                }
                data_opciones.append(opt_data)

            if data_opciones:
                item_data["opciones"] = data_opciones

            data_items.append(item_data)

        data["items"] = data_items
        return data
