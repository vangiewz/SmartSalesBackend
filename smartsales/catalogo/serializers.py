from rest_framework import serializers


class ImportarCatalogoSerializer(serializers.Serializer):
    """
    Serializer para la importación de catálogo desde archivo Excel.
    El archivo debe seguir la plantilla descargada.
    """
    archivo = serializers.FileField(
        required=True,
        help_text="Archivo Excel (.xlsx) con el catálogo de productos"
    )
    
    def validate_archivo(self, value):
        """Validar que el archivo sea Excel"""
        if not value.name.endswith(('.xlsx', '.xls')):
            raise serializers.ValidationError(
                "El archivo debe ser de formato Excel (.xlsx o .xls)"
            )
        
        # Validar tamaño (máximo 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError(
                "El archivo no debe superar los 10MB"
            )
        
        return value


class ResultadoImportacionSerializer(serializers.Serializer):
    """Serializer para mostrar el resultado de la importación"""
    total_procesados = serializers.IntegerField()
    exitosos = serializers.IntegerField()
    fallidos = serializers.IntegerField()
    errores = serializers.ListField(
        child=serializers.DictField(),
        help_text="Lista de errores encontrados durante la importación"
    )
    productos_creados = serializers.ListField(
        child=serializers.DictField(),
        help_text="Lista de productos creados exitosamente"
    )


class ProductoExportadoSerializer(serializers.Serializer):
    """Serializer para un producto exportado"""
    id = serializers.IntegerField()
    nombre = serializers.CharField()
    precio = serializers.DecimalField(max_digits=12, decimal_places=2)
    stock = serializers.IntegerField()
    tiempo_garantia = serializers.IntegerField()
    marca = serializers.CharField()
    tipo_producto = serializers.CharField()
