from django.db import connection
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .serializers import HistorialPagoSerializer


class HistorialPagosView(APIView):
    """
    Vista para obtener el historial de pagos del usuario autenticado.
    Muestra todos los pagos realizados con sus detalles.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        usuario_id = request.user.id
        
        with connection.cursor() as cursor:
            # Obtener todos los pagos del usuario con detalles
            cursor.execute("""
                SELECT 
                    p.id AS pago_id,
                    p.venta_id,
                    p.total,
                    p.hora AS fecha_pago,
                    v.hora AS fecha_venta,
                    v.direccion,
                    v.usuario_id,
                    p.receipt_url
                FROM pagos p
                INNER JOIN venta v ON p.venta_id = v.id
                WHERE v.usuario_id = %s
                ORDER BY p.hora DESC
            """, [usuario_id])
            
            pagos_rows = cursor.fetchall()
            
            if not pagos_rows:
                return Response([], status=status.HTTP_200_OK)
            
            # Construir respuesta con detalles de cada pago
            historial = []
            
            for row in pagos_rows:
                pago_id, venta_id, total, fecha_pago, fecha_venta, direccion, _, receipt_url = row
                
                # Obtener productos de esta venta
                cursor.execute("""
                    SELECT 
                        dv.producto_id,
                        prod.nombre AS producto_nombre,
                        dv.cantidad,
                        prod.precio AS precio_unitario,
                        (prod.precio * dv.cantidad) AS subtotal
                    FROM detalleventa dv
                    INNER JOIN producto prod ON dv.producto_id = prod.id
                    WHERE dv.venta_id = %s
                """, [venta_id])
                
                productos_rows = cursor.fetchall()
                
                productos = [
                    {
                        'producto_id': p[0],
                        'producto_nombre': p[1],
                        'cantidad': p[2],
                        'precio_unitario': float(p[3]),
                        'subtotal': float(p[4])
                    }
                    for p in productos_rows
                ]
                
                historial.append({
                    'pago_id': pago_id,
                    'venta_id': venta_id,
                    'total': float(total),
                    'fecha_pago': fecha_pago,
                    'fecha_venta': fecha_venta,
                    'direccion_envio': direccion,
                    'productos': productos,
                    'receipt_url': receipt_url  # Ahora viene de la base de datos
                })
        
        serializer = HistorialPagoSerializer(historial, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DetallePagoView(APIView):
    """
    Vista para obtener el detalle de un pago específico.
    Solo el usuario propietario puede ver sus pagos.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pago_id):
        usuario_id = request.user.id
        
        with connection.cursor() as cursor:
            # Verificar que el pago pertenece al usuario
            cursor.execute("""
                SELECT 
                    p.id AS pago_id,
                    p.venta_id,
                    p.total,
                    p.hora AS fecha_pago,
                    v.hora AS fecha_venta,
                    v.direccion,
                    v.usuario_id,
                    p.receipt_url
                FROM pagos p
                INNER JOIN venta v ON p.venta_id = v.id
                WHERE p.id = %s AND v.usuario_id = %s
            """, [pago_id, usuario_id])
            
            pago_row = cursor.fetchone()
            
            if not pago_row:
                return Response(
                    {"detail": "Pago no encontrado o no pertenece al usuario."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            pago_id, venta_id, total, fecha_pago, fecha_venta, direccion, _, receipt_url = pago_row
            
            # Obtener productos de esta venta
            cursor.execute("""
                SELECT 
                    dv.producto_id,
                    prod.nombre AS producto_nombre,
                    dv.cantidad,
                    prod.precio AS precio_unitario,
                    (prod.precio * dv.cantidad) AS subtotal
                FROM detalleventa dv
                INNER JOIN producto prod ON dv.producto_id = prod.id
                WHERE dv.venta_id = %s
            """, [venta_id])
            
            productos_rows = cursor.fetchall()
            
            productos = [
                {
                    'producto_id': p[0],
                    'producto_nombre': p[1],
                    'cantidad': p[2],
                    'precio_unitario': float(p[3]),
                    'subtotal': float(p[4])
                }
                for p in productos_rows
            ]
            
            detalle = {
                'pago_id': pago_id,
                'venta_id': venta_id,
                'total': float(total),
                'fecha_pago': fecha_pago,
                'fecha_venta': fecha_venta,
                'direccion_envio': direccion,
                'productos': productos,
                'receipt_url': receipt_url  # Ahora viene de la base de datos
            }
        
        serializer = HistorialPagoSerializer(detalle)
        return Response(serializer.data, status=status.HTTP_200_OK)
