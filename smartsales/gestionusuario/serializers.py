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
