from rest_framework import serializers


class DireccionSerializer(serializers.Serializer):
    """Serializer para validar direcciones de usuario"""
    direccion = serializers.CharField(max_length=500, min_length=5)
