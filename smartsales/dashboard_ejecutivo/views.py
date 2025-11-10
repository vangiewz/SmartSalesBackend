from datetime import datetime, timedelta
from decimal import Decimal

from django.db import connection
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from smartsales.rolesusuario.permissions import (
    IsAnalistaRole,
    IsAdminRole,
    user_has_any_role,
    ROLE_ADMIN_NAME,
    ROLE_ANALISTA_NAME
)
from .serializers import (
    FiltrosDashboardSerializer,
    DashboardEjecutivoSerializer,
)


class PermisoDashboard(IsAuthenticated):
    """Permiso personalizado para Analista o Administrador"""
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        uid = getattr(request.user, "id", None)
        return user_has_any_role(uid, [ROLE_ADMIN_NAME, ROLE_ANALISTA_NAME])


class DashboardEjecutivoView(APIView):
    """
    Vista principal del dashboard ejecutivo.
    Proporciona KPIs, gráficos y alertas para gerentes y analistas.
    
    GET /api/dashboard-ejecutivo/?periodo=mes
    GET /api/dashboard-ejecutivo/?fecha_inicio=2024-01-01&fecha_fin=2024-12-31
    """
    permission_classes = [PermisoDashboard]
    
    def get(self, request):
        # Validar filtros
        filtros_serializer = FiltrosDashboardSerializer(data=request.query_params)
        filtros_serializer.is_valid(raise_exception=True)
        
        # Calcular rango de fechas
        fecha_inicio, fecha_fin, periodo_nombre = self._calcular_periodo(
            filtros_serializer.validated_data
        )
        
        # Obtener todos los datos del dashboard
        kpis = self._obtener_kpis(fecha_inicio, fecha_fin)
        ventas_por_dia = self._obtener_ventas_por_dia(fecha_inicio, fecha_fin)
        productos_mas_vendidos = self._obtener_productos_mas_vendidos(fecha_inicio, fecha_fin)
        ventas_por_categoria = self._obtener_ventas_por_categoria(fecha_inicio, fecha_fin)
        mejores_clientes = self._obtener_mejores_clientes(fecha_inicio, fecha_fin)
        alertas = self._obtener_alertas()
        resumen = self._obtener_resumen(fecha_inicio, fecha_fin)
        
        # Construir respuesta
        dashboard_data = {
            'periodo': periodo_nombre,
            'fecha_actualizacion': timezone.now(),
            'kpis': kpis,
            'ventas_por_dia': ventas_por_dia,
            'productos_mas_vendidos': productos_mas_vendidos,
            'ventas_por_categoria': ventas_por_categoria,
            'mejores_clientes': mejores_clientes,
            'alertas': alertas,
            'resumen': resumen
        }
        
        return Response(
            DashboardEjecutivoSerializer(dashboard_data).data,
            status=status.HTTP_200_OK
        )
    
    def _calcular_periodo(self, filtros):
        """Calcula el rango de fechas según los filtros"""
        periodo = filtros.get('periodo', 'mes')
        ahora = timezone.now()
        
        if filtros.get('fecha_inicio') and filtros.get('fecha_fin'):
            return (
                filtros['fecha_inicio'],
                filtros['fecha_fin'],
                f"Del {filtros['fecha_inicio'].strftime('%d/%m/%Y')} al {filtros['fecha_fin'].strftime('%d/%m/%Y')}"
            )
        
        if periodo == 'hoy':
            inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
            fin = ahora
            nombre = "Hoy"
        elif periodo == 'semana':
            inicio = ahora - timedelta(days=7)
            fin = ahora
            nombre = "Última semana"
        elif periodo == 'mes':
            inicio = ahora - timedelta(days=30)
            fin = ahora
            nombre = "Último mes"
        elif periodo == 'trimestre':
            inicio = ahora - timedelta(days=90)
            fin = ahora
            nombre = "Último trimestre"
        elif periodo == 'año':
            inicio = ahora - timedelta(days=365)
            fin = ahora
            nombre = "Último año"
        else:  # 'todo'
            inicio = datetime(2020, 1, 1, tzinfo=timezone.utc)
            fin = ahora
            nombre = "Todo el período"
        
        return inicio, fin, nombre
    
    def _obtener_kpis(self, fecha_inicio, fecha_fin):
        """Obtiene los KPIs principales"""
        with connection.cursor() as cursor:
            # Total de ventas y monto
            cursor.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(total), 0)
                FROM venta
                WHERE hora BETWEEN %s AND %s
                """,
                [fecha_inicio, fecha_fin]
            )
            total_ventas, monto_ventas = cursor.fetchone()
            
            # Comparar con período anterior
            duracion = (fecha_fin - fecha_inicio).days
            fecha_inicio_anterior = fecha_inicio - timedelta(days=duracion)
            fecha_fin_anterior = fecha_inicio
            
            cursor.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(total), 0)
                FROM venta
                WHERE hora BETWEEN %s AND %s
                """,
                [fecha_inicio_anterior, fecha_fin_anterior]
            )
            total_ventas_anterior, monto_ventas_anterior = cursor.fetchone()
            
            # Calcular cambio porcentual
            cambio_ventas = self._calcular_cambio(total_ventas, total_ventas_anterior)
            cambio_monto = self._calcular_cambio(float(monto_ventas), float(monto_ventas_anterior))
            
            # Total de clientes
            cursor.execute(
                """
                SELECT COUNT(DISTINCT usuario_id)
                FROM venta
                WHERE hora BETWEEN %s AND %s
                """,
                [fecha_inicio, fecha_fin]
            )
            total_clientes = cursor.fetchone()[0]
            
            cursor.execute(
                """
                SELECT COUNT(DISTINCT usuario_id)
                FROM venta
                WHERE hora BETWEEN %s AND %s
                """,
                [fecha_inicio_anterior, fecha_fin_anterior]
            )
            total_clientes_anterior = cursor.fetchone()[0]
            cambio_clientes = self._calcular_cambio(total_clientes, total_clientes_anterior)
            
            # Ticket promedio
            ticket_promedio = float(monto_ventas) / total_ventas if total_ventas > 0 else 0
            ticket_promedio_anterior = float(monto_ventas_anterior) / total_ventas_anterior if total_ventas_anterior > 0 else 0
            cambio_ticket = self._calcular_cambio(ticket_promedio, ticket_promedio_anterior)
            
            # Productos vendidos
            cursor.execute(
                """
                SELECT COALESCE(SUM(dv.cantidad), 0)
                FROM detalleventa dv
                JOIN venta v ON v.id = dv.venta_id
                WHERE v.hora BETWEEN %s AND %s
                """,
                [fecha_inicio, fecha_fin]
            )
            productos_vendidos = cursor.fetchone()[0]
            
            # Garantías pendientes
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM garantia g
                JOIN estadogarantia eg ON eg.id = g.estadogarantia_id
                WHERE eg.nombre = 'Pendiente'
                """
            )
            garantias_pendientes = cursor.fetchone()[0]
        
        kpis = [
            {
                'titulo': 'Ventas Totales',
                'valor': f"${monto_ventas:,.2f}",
                'cambio_porcentual': cambio_monto,
                'tendencia': self._obtener_tendencia(cambio_monto),
                'icono': 'dollar'
            },
            {
                'titulo': 'Número de Ventas',
                'valor': str(total_ventas),
                'cambio_porcentual': cambio_ventas,
                'tendencia': self._obtener_tendencia(cambio_ventas),
                'icono': 'shopping-cart'
            },
            {
                'titulo': 'Clientes Activos',
                'valor': str(total_clientes),
                'cambio_porcentual': cambio_clientes,
                'tendencia': self._obtener_tendencia(cambio_clientes),
                'icono': 'users'
            },
            {
                'titulo': 'Ticket Promedio',
                'valor': f"${ticket_promedio:,.2f}",
                'cambio_porcentual': cambio_ticket,
                'tendencia': self._obtener_tendencia(cambio_ticket),
                'icono': 'receipt'
            },
            {
                'titulo': 'Productos Vendidos',
                'valor': str(productos_vendidos),
                'cambio_porcentual': None,
                'tendencia': None,
                'icono': 'package'
            },
            {
                'titulo': 'Garantías Pendientes',
                'valor': str(garantias_pendientes),
                'cambio_porcentual': None,
                'tendencia': None,
                'icono': 'alert-circle'
            }
        ]
        
        return kpis
    
    def _obtener_ventas_por_dia(self, fecha_inicio, fecha_fin):
        """Obtiene las ventas agrupadas por día"""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    DATE(hora) as fecha,
                    COUNT(*) as total_ventas,
                    COALESCE(SUM(total), 0) as monto_total
                FROM venta
                WHERE hora BETWEEN %s AND %s
                GROUP BY DATE(hora)
                ORDER BY fecha
                """,
                [fecha_inicio, fecha_fin]
            )
            rows = cursor.fetchall()
        
        return [
            {
                'fecha': row[0],
                'total_ventas': row[1],
                'monto_total': row[2]
            }
            for row in rows
        ]
    
    def _obtener_productos_mas_vendidos(self, fecha_inicio, fecha_fin, limite=10):
        """Obtiene los productos más vendidos"""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    p.id,
                    p.nombre,
                    SUM(dv.cantidad) as cantidad_vendida,
                    SUM(dv.cantidad * p.precio) as monto_total,
                    m.nombre as marca
                FROM detalleventa dv
                JOIN venta v ON v.id = dv.venta_id
                JOIN producto p ON p.id = dv.producto_id
                JOIN marca m ON m.id = p.marca_id
                WHERE v.hora BETWEEN %s AND %s
                GROUP BY p.id, p.nombre, m.nombre
                ORDER BY cantidad_vendida DESC
                LIMIT %s
                """,
                [fecha_inicio, fecha_fin, limite]
            )
            rows = cursor.fetchall()
        
        return [
            {
                'producto_id': row[0],
                'nombre': row[1],
                'cantidad_vendida': row[2],
                'monto_total': row[3],
                'marca': row[4]
            }
            for row in rows
        ]
    
    def _obtener_ventas_por_categoria(self, fecha_inicio, fecha_fin):
        """Obtiene las ventas agrupadas por tipo de producto"""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    tp.nombre as categoria,
                    SUM(dv.cantidad) as cantidad,
                    SUM(dv.cantidad * p.precio) as monto
                FROM detalleventa dv
                JOIN venta v ON v.id = dv.venta_id
                JOIN producto p ON p.id = dv.producto_id
                JOIN tipoproducto tp ON tp.id = p.tipoproducto_id
                WHERE v.hora BETWEEN %s AND %s
                GROUP BY tp.nombre
                ORDER BY monto DESC
                """,
                [fecha_inicio, fecha_fin]
            )
            rows = cursor.fetchall()
        
        # Calcular porcentajes
        total_monto = sum(float(row[2]) for row in rows)
        
        return [
            {
                'categoria': row[0],
                'cantidad': row[1],
                'monto': row[2],
                'porcentaje': (float(row[2]) / total_monto * 100) if total_monto > 0 else 0
            }
            for row in rows
        ]
    
    def _obtener_mejores_clientes(self, fecha_inicio, fecha_fin, limite=10):
        """Obtiene los clientes con más compras"""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    u.id,
                    u.nombre,
                    u.correo,
                    COUNT(v.id) as total_compras,
                    SUM(v.total) as monto_total
                FROM venta v
                JOIN usuario u ON u.id = v.usuario_id
                WHERE v.hora BETWEEN %s AND %s
                GROUP BY u.id, u.nombre, u.correo
                ORDER BY monto_total DESC
                LIMIT %s
                """,
                [fecha_inicio, fecha_fin, limite]
            )
            rows = cursor.fetchall()
        
        return [
            {
                'cliente_id': row[0],
                'nombre': row[1],
                'correo': row[2],
                'total_compras': row[3],
                'monto_total': row[4]
            }
            for row in rows
        ]
    
    def _obtener_alertas(self):
        """Obtiene las alertas recientes del sistema"""
        alertas = []
        
        with connection.cursor() as cursor:
            # Productos con stock bajo (7 o menos)
            cursor.execute(
                """
                SELECT p.id, p.nombre, p.stock, u.nombre as vendedor
                FROM producto p
                JOIN usuario u ON u.id = p.id_vendedor
                WHERE p.stock <= 7 AND p.stock > 0
                ORDER BY p.stock ASC
                LIMIT 5
                """
            )
            for row in cursor.fetchall():
                alertas.append({
                    'tipo': 'stock_bajo',
                    'titulo': f'Stock bajo: {row[1]}',
                    'descripcion': f'Quedan {row[2]} unidades. Vendedor: {row[3]}',
                    'fecha': timezone.now(),
                    'severidad': 'warning'
                })
            
            # Productos sin stock
            cursor.execute(
                """
                SELECT p.id, p.nombre, u.nombre as vendedor
                FROM producto p
                JOIN usuario u ON u.id = p.id_vendedor
                WHERE p.stock = 0
                ORDER BY p.nombre
                LIMIT 5
                """
            )
            for row in cursor.fetchall():
                alertas.append({
                    'tipo': 'stock_bajo',
                    'titulo': f'Sin stock: {row[1]}',
                    'descripcion': f'Producto agotado. Vendedor: {row[2]}',
                    'fecha': timezone.now(),
                    'severidad': 'error'
                })
            
            # Garantías pendientes
            cursor.execute(
                """
                SELECT g.id, p.nombre, u.nombre as cliente, g.hora
                FROM garantia g
                JOIN estadogarantia eg ON eg.id = g.estadogarantia_id
                JOIN producto p ON p.id = g.producto_id
                JOIN venta v ON v.id = g.venta_id
                JOIN usuario u ON u.id = v.usuario_id
                WHERE eg.nombre = 'Pendiente'
                ORDER BY g.hora DESC
                LIMIT 5
                """
            )
            for row in cursor.fetchall():
                alertas.append({
                    'tipo': 'garantia_pendiente',
                    'titulo': f'Garantía pendiente: {row[1]}',
                    'descripcion': f'Cliente: {row[2]}',
                    'fecha': row[3],
                    'severidad': 'warning'
                })
            
            # Ventas destacadas del día (mayores a $500)
            cursor.execute(
                """
                SELECT v.id, v.total, u.nombre as cliente, v.hora
                FROM venta v
                JOIN usuario u ON u.id = v.usuario_id
                WHERE v.hora >= NOW() - INTERVAL '1 day'
                AND v.total > 500
                ORDER BY v.total DESC
                LIMIT 3
                """
            )
            for row in cursor.fetchall():
                alertas.append({
                    'tipo': 'venta_alta',
                    'titulo': f'Venta destacada: ${row[1]}',
                    'descripcion': f'Cliente: {row[2]}',
                    'fecha': row[3],
                    'severidad': 'info'
                })
        
        return alertas
    
    def _obtener_resumen(self, fecha_inicio, fecha_fin):
        """Obtiene un resumen general del sistema"""
        with connection.cursor() as cursor:
            # Total de productos en catálogo
            cursor.execute("SELECT COUNT(*) FROM producto")
            total_productos = cursor.fetchone()[0]
            
            # Total de usuarios registrados
            cursor.execute("SELECT COUNT(*) FROM usuario")
            total_usuarios = cursor.fetchone()[0]
            
            # Total de vendedores
            cursor.execute(
                """
                SELECT COUNT(DISTINCT ru.usuario_id)
                FROM rolesusuario ru
                JOIN roles r ON r.id = ru.rol_id
                WHERE LOWER(r.nombre) = 'vendedor'
                """
            )
            total_vendedores = cursor.fetchone()[0]
            
            # Valor total del inventario
            cursor.execute(
                "SELECT COALESCE(SUM(precio * stock), 0) FROM producto"
            )
            valor_inventario = cursor.fetchone()[0]
        
        return {
            'total_productos': total_productos,
            'total_usuarios': total_usuarios,
            'total_vendedores': total_vendedores,
            'valor_inventario': float(valor_inventario)
        }
    
    def _calcular_cambio(self, actual, anterior):
        """Calcula el cambio porcentual entre dos valores"""
        if anterior == 0:
            return 100.0 if actual > 0 else 0.0
        return ((actual - anterior) / anterior) * 100
    
    def _obtener_tendencia(self, cambio):
        """Determina la tendencia según el cambio porcentual"""
        if cambio is None:
            return None
        if cambio > 2:
            return 'up'
        elif cambio < -2:
            return 'down'
        else:
            return 'stable'
