"""
Serializers para el sistema de notificaciones
"""
from rest_framework import serializers
from .models import SuscripcionMovil, ColaNotificacion


class SuscripcionMovilSerializer(serializers.ModelSerializer):
    """
    Serializer para suscripciones móviles
    """
    class Meta:
        model = SuscripcionMovil
        fields = ['id', 'usuario', 'token_dispositivo', 'activo', 'creado_en', 'actualizado_en']
        read_only_fields = ['id', 'creado_en', 'actualizado_en']


class ColaNotificacionSerializer(serializers.ModelSerializer):
    """
    Serializer para cola de notificaciones
    """
    class Meta:
        model = ColaNotificacion
        fields = [
            'id', 'usuario', 'canal', 'titulo', 'cuerpo', 'datos',
            'estado', 'reintentos', 'max_reintentos', 'proximo_intento',
            'creado_en', 'actualizado_en'
        ]
        read_only_fields = ['id', 'creado_en', 'actualizado_en']


class ActualizarTokenSerializer(serializers.Serializer):
    """
    Serializer para actualizar el token de dispositivo móvil
    """
    token_dispositivo = serializers.CharField(max_length=500, required=True)
