"""
Serializers para recuperación de contraseña - SIMPLE.
"""
from rest_framework import serializers


class PasswordResetRequestSerializer(serializers.Serializer):
    """Validación para solicitar recuperación."""
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Validación para confirmar cambio de contraseña."""
    token = serializers.CharField(required=True, min_length=20)
    new_password = serializers.CharField(required=True, write_only=True, min_length=6)
