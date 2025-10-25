from rest_framework import serializers


class ItemCheckoutSerializer(serializers.Serializer):
    """Serializer para un item individual en el carrito"""
    producto_id = serializers.IntegerField()  # ✅ Cambiado de id_producto a producto_id
    cantidad = serializers.IntegerField(min_value=1)


class IniciarCheckoutSerializer(serializers.Serializer):
    """Serializer para iniciar el proceso de checkout"""
    items = serializers.ListField(
        child=ItemCheckoutSerializer(),
        min_length=1
    )
    id_direccion = serializers.IntegerField(required=False, allow_null=True)
    direccion_manual = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        max_length=500
    )

    def validate(self, data):
        """
        Validar que se proporcione id_direccion O direccion_manual,
        pero no ambos y al menos uno.
        """
        id_dir = data.get('id_direccion')
        txt_dir = data.get('direccion_manual')
        
        # Remover valores vacíos/None
        has_id = id_dir is not None
        has_txt = txt_dir and txt_dir.strip()
        
        if not has_id and not has_txt:
            raise serializers.ValidationError(
                "Debe proporcionar 'id_direccion' o 'direccion_manual'."
            )
        
        if has_id and has_txt:
            raise serializers.ValidationError(
                "No puede proporcionar 'id_direccion' y 'direccion_manual' al mismo tiempo."
            )
        
        return data
