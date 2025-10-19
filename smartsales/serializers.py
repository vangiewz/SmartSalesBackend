from rest_framework import serializers

class UsuarioMeSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    nombre = serializers.CharField()
    telefono = serializers.CharField(allow_null=True, allow_blank=True)
    correo = serializers.EmailField()
    roles = serializers.ListField(child=serializers.CharField(), read_only=True)

class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    nombre = serializers.CharField(max_length=120)
    telefono = serializers.CharField(max_length=40, required=False, allow_blank=True)

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
