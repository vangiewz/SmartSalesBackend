# smartsales/garantia/ventas_elegibles.py
from datetime import timedelta
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from smartsales.db_utils import execute_query_with_retry

try:
    from smartsales.gestionproducto.storage import public_url
except Exception:
    def public_url(key): 
        return key if key else ""

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ventas_elegibles_garantia(request):
    """
    Retorna las ventas del usuario con productos elegibles para garantía.
    
    Un producto es elegible si:
    1. Tiene garantía (tiempogarantia > 0)
    2. La garantía no ha expirado (limitegarantia > NOW())
    3. No tiene una garantía pendiente o completada
    """
    usuario_id = request.user.id
    
    # Query para obtener ventas con productos elegibles
    query = """
    SELECT DISTINCT
        v.id AS venta_id,
        v.hora AS fecha_venta,
        dv.producto_id,
        p.nombre AS producto_nombre,
        COALESCE(p.imagen_key, '') AS imagen_key,
        dv.cantidad AS cantidad_comprada,
        dv.limitegarantia
    FROM venta v
    JOIN detalleventa dv ON dv.venta_id = v.id
    JOIN producto p ON p.id = dv.producto_id
    LEFT JOIN garantia g ON g.venta_id = v.id 
        AND g.producto_id = dv.producto_id 
        AND g.estadogarantia_id IN (
            SELECT id FROM estadogarantia WHERE nombre IN ('Pendiente', 'Completado')
        )
    WHERE v.usuario_id = %s
        AND p.tiempogarantia > 0
        AND dv.limitegarantia > NOW()
        AND g.id IS NULL
    ORDER BY v.hora DESC, p.nombre ASC
    """
    
    rows = execute_query_with_retry(query, [usuario_id], fetch_all=True)
    
    # Agrupar por venta_id
    ventas_map = {}
    for row in rows:
        venta_id, fecha_venta, producto_id, producto_nombre, imagen_key, cantidad_comprada, limitegarantia = row
        
        if venta_id not in ventas_map:
            ventas_map[venta_id] = {
                'venta_id': venta_id,
                'fecha_venta': fecha_venta.isoformat() if fecha_venta else None,
                'productos': []
            }
        
        ventas_map[venta_id]['productos'].append({
            'producto_id': producto_id,
            'producto_nombre': producto_nombre,
            'producto_imagen_url': public_url(imagen_key) if imagen_key else '',
            'cantidad_comprada': cantidad_comprada,
            'limitegarantia': limitegarantia.isoformat() if limitegarantia else None
        })
    
    ventas_elegibles = list(ventas_map.values())
    return Response(ventas_elegibles)
