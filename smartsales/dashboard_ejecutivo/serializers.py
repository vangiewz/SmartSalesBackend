from rest_framework import serializers
from datetime import datetime


class FiltrosDashboardSerializer(serializers.Serializer):
    """Serializer para filtros del dashboard"""
    fecha_inicio = serializers.DateTimeField(
        required=False,
        help_text="Fecha de inicio para filtrar datos (formato: YYYY-MM-DD o ISO 8601)"
    )
    fecha_fin = serializers.DateTimeField(
        required=False,
        help_text="Fecha de fin para filtrar datos (formato: YYYY-MM-DD o ISO 8601)"
    )
    periodo = serializers.ChoiceField(
        choices=['hoy', 'semana', 'mes', 'trimestre', 'año', 'todo'],
        required=False,
        default='mes',
        help_text="Período predefinido (sobrescribe fecha_inicio y fecha_fin)"
    )
    
    def validate(self, data):
        """Validar que las fechas sean coherentes"""
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')
        
        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            raise serializers.ValidationError(
                "La fecha de inicio no puede ser posterior a la fecha de fin"
            )
        
        return data


class KPISerializer(serializers.Serializer):
    """Serializer para un KPI individual"""
    titulo = serializers.CharField()
    valor = serializers.CharField()
    cambio_porcentual = serializers.FloatField(allow_null=True)
    tendencia = serializers.ChoiceField(
        choices=['up', 'down', 'stable'],
        allow_null=True
    )
    icono = serializers.CharField()


class VentasPorDiaSerializer(serializers.Serializer):
    """Serializer para ventas diarias"""
    fecha = serializers.DateField()
    total_ventas = serializers.IntegerField()
    monto_total = serializers.DecimalField(max_digits=12, decimal_places=2)


class ProductoMasVendidoSerializer(serializers.Serializer):
    """Serializer para productos más vendidos"""
    producto_id = serializers.IntegerField()
    nombre = serializers.CharField()
    cantidad_vendida = serializers.IntegerField()
    monto_total = serializers.DecimalField(max_digits=12, decimal_places=2)
    marca = serializers.CharField()


class ClienteTopSerializer(serializers.Serializer):
    """Serializer para mejores clientes"""
    cliente_id = serializers.UUIDField()
    nombre = serializers.CharField()
    correo = serializers.EmailField()
    total_compras = serializers.IntegerField()
    monto_total = serializers.DecimalField(max_digits=12, decimal_places=2)


class VentasPorCategoriaSerializer(serializers.Serializer):
    """Serializer para ventas por categoría"""
    categoria = serializers.CharField()
    cantidad = serializers.IntegerField()
    monto = serializers.DecimalField(max_digits=12, decimal_places=2)
    porcentaje = serializers.FloatField()


class AlertaSerializer(serializers.Serializer):
    """Serializer para alertas del sistema"""
    tipo = serializers.ChoiceField(choices=['stock_bajo', 'garantia_pendiente', 'venta_alta'])
    titulo = serializers.CharField()
    descripcion = serializers.CharField()
    fecha = serializers.DateTimeField()
    severidad = serializers.ChoiceField(choices=['info', 'warning', 'error'])


class DashboardEjecutivoSerializer(serializers.Serializer):
    """Serializer completo para el dashboard ejecutivo"""
    periodo = serializers.CharField()
    fecha_actualizacion = serializers.DateTimeField()
    
    # KPIs principales
    kpis = serializers.ListField(child=KPISerializer())
    
    # Gráficos
    ventas_por_dia = serializers.ListField(child=VentasPorDiaSerializer())
    productos_mas_vendidos = serializers.ListField(child=ProductoMasVendidoSerializer())
    ventas_por_categoria = serializers.ListField(child=VentasPorCategoriaSerializer())
    mejores_clientes = serializers.ListField(child=ClienteTopSerializer())
    
    # Alertas recientes
    alertas = serializers.ListField(child=AlertaSerializer())
    
    # Resumen general
    resumen = serializers.DictField()
