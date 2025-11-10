from rest_framework import serializers


# ==================== TIPO DE PRODUCTO ====================

class TipoProductoSerializer(serializers.Serializer):
    """Serializer para mostrar un tipo de producto"""
    id = serializers.IntegerField(read_only=True)
    nombre = serializers.CharField(max_length=120)


class CrearTipoProductoSerializer(serializers.Serializer):
    """Serializer para crear un nuevo tipo de producto"""
    nombre = serializers.CharField(
        max_length=120,
        required=True,
        help_text="Nombre del tipo de producto (ej: Refrigerador, Laptop, etc.)"
    )
    
    def validate_nombre(self, value):
        """Validar que el nombre no esté vacío"""
        nombre = value.strip()
        if not nombre:
            raise serializers.ValidationError("El nombre no puede estar vacío.")
        if len(nombre) > 120:
            raise serializers.ValidationError("El nombre no puede superar 120 caracteres.")
        return nombre


class ActualizarTipoProductoSerializer(serializers.Serializer):
    """Serializer para actualizar un tipo de producto existente"""
    nombre = serializers.CharField(
        max_length=120,
        required=True,
        help_text="Nuevo nombre del tipo de producto"
    )
    
    def validate_nombre(self, value):
        """Validar que el nombre no esté vacío"""
        nombre = value.strip()
        if not nombre:
            raise serializers.ValidationError("El nombre no puede estar vacío.")
        if len(nombre) > 120:
            raise serializers.ValidationError("El nombre no puede superar 120 caracteres.")
        return nombre


# ==================== MARCA ====================

class MarcaSerializer(serializers.Serializer):
    """Serializer para mostrar una marca"""
    id = serializers.IntegerField(read_only=True)
    nombre = serializers.CharField(max_length=120)


class CrearMarcaSerializer(serializers.Serializer):
    """Serializer para crear una nueva marca"""
    nombre = serializers.CharField(
        max_length=120,
        required=True,
        help_text="Nombre de la marca (ej: Samsung, LG, Sony, etc.)"
    )
    
    def validate_nombre(self, value):
        """Validar que el nombre no esté vacío"""
        nombre = value.strip()
        if not nombre:
            raise serializers.ValidationError("El nombre no puede estar vacío.")
        if len(nombre) > 120:
            raise serializers.ValidationError("El nombre no puede superar 120 caracteres.")
        return nombre


class ActualizarMarcaSerializer(serializers.Serializer):
    """Serializer para actualizar una marca existente"""
    nombre = serializers.CharField(
        max_length=120,
        required=True,
        help_text="Nuevo nombre de la marca"
    )
    
    def validate_nombre(self, value):
        """Validar que el nombre no esté vacío"""
        nombre = value.strip()
        if not nombre:
            raise serializers.ValidationError("El nombre no puede estar vacío.")
        if len(nombre) > 120:
            raise serializers.ValidationError("El nombre no puede superar 120 caracteres.")
        return nombre
