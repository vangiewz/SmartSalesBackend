from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import Usuario

class UsuarioMeSerializer(serializers.ModelSerializer):
    roles = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = Usuario
        fields = ["id", "nombre", "telefono", "correo", "roles"]

class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    nombre = serializers.CharField(max_length=120)
    telefono = serializers.CharField(max_length=40, required=False, allow_blank=True)

    def validate_email(self, v):
        v = v.strip().lower()
        if User.objects.filter(email__iexact=v).exists():
            raise serializers.ValidationError("Ese email ya está registrado.")
        return v

    def validate_password(self, v):
        validate_password(v)
        return v

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
