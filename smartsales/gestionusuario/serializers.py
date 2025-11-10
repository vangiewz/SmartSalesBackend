from rest_framework import serializers

class UsuarioItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    correo = serializers.EmailField()
    nombre = serializers.CharField(allow_null=True)
    telefono = serializers.CharField(allow_null=True, allow_blank=True)
    roles = serializers.ListField(child=serializers.CharField())
    roles_ids = serializers.ListField(child=serializers.IntegerField())

class UsuarioListQuerySerializer(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=200)
    offset = serializers.IntegerField(required=False, min_value=0)

class UsuarioPerfilUpdateSerializer(serializers.Serializer):
    nombre = serializers.CharField(required=False, allow_blank=False, max_length=120)
    telefono = serializers.CharField(required=False, allow_blank=True, max_length=40)

class UsuarioRolesPutSerializer(serializers.Serializer):
    roles_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=True)

class UsuarioRolAddSerializer(serializers.Serializer):
    rol_id = serializers.IntegerField()


# --------------- CAMBIO DE CONTRASEÑA ---------------

class UsuarioChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError("Las contraseñas no coinciden.")
        if attrs["current_password"] == attrs["new_password"]:
            raise serializers.ValidationError(
                "La nueva contraseña debe ser diferente a la actual."
            )
        return attrs


class UsuarioPerfilSerializer(serializers.Serializer):
    """Para mostrar perfil básico en /mi-perfil/"""
    id = serializers.UUIDField(read_only=True)
    correo = serializers.EmailField(read_only=True)
    nombre = serializers.CharField(required=False, allow_blank=True, max_length=120)
    telefono = serializers.CharField(required=False, allow_blank=True, max_length=40)


