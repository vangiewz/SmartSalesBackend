from rest_framework import serializers

class MisRolesResponseSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    correo = serializers.EmailField()
    nombre = serializers.CharField(allow_null=True)
    telefono = serializers.CharField(allow_null=True, allow_blank=True)
    roles = serializers.ListField(child=serializers.CharField())
    roles_ids = serializers.ListField(child=serializers.IntegerField())
    is_admin = serializers.BooleanField()
    is_vendedor = serializers.BooleanField()
    is_analista = serializers.BooleanField()
    is_usuario = serializers.BooleanField()

class CheckRoleQuerySerializer(serializers.Serializer):
    role_id = serializers.IntegerField(required=False)
    role_name = serializers.CharField(required=False)

class CheckRoleResponseSerializer(serializers.Serializer):
    has_role = serializers.BooleanField()
    role_id = serializers.IntegerField(allow_null=True)
    role_name = serializers.CharField(allow_null=True)
