from rest_framework import serializers
from django.db import transaction
from django.db.models import Q
from .models import Usuario, UsuarioRol

# Constantes: actualizar según tu esquema
CLIENT_ROLE_ID = 1  # según tu comentario: rol_id == 1 => cliente

class ClienteListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ("id", "nombre", "telefono", "correo")


class ClienteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ("nombre", "telefono", "correo")

    def validate(self, data):
        correo = data.get("correo")
        telefono = data.get("telefono")
        q = Q()
        if correo:
            q |= Q(correo__iexact=correo)
        if telefono:
            q |= Q(telefono__iexact=telefono)
        if q:
            dup = Usuario.objects.filter(q).first()
            if dup:
                raise serializers.ValidationError("Cliente duplicado: correo o teléfono ya registrado.")
        return data

    def create(self, validated_data):
        # Crear usuario y asignar rol cliente
        with transaction.atomic():
            user = Usuario.objects.create(**validated_data)
            UsuarioRol.objects.create(usuario_id=user.id, rol_id=CLIENT_ROLE_ID, role="cliente")
        return user


class ClienteUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ("nombre", "telefono", "correo")

    def validate(self, data):
        correo = data.get("correo", None)
        telefono = data.get("telefono", None)
        # Excluir al propio registro al chequear duplicados
        instancia = getattr(self, "instance", None)
        q = Q()
        if correo:
            q |= Q(correo__iexact=correo)
        if telefono:
            q |= Q(telefono__iexact=telefono)
        if q:
            qs = Usuario.objects.filter(q)
            if instancia:
                qs = qs.exclude(id=instancia.id)
            if qs.exists():
                raise serializers.ValidationError("Cliente duplicado: correo o teléfono ya registrado.")
        return data