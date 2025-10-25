from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from smartsales.db_utils import execute_query_with_retry
from smartsales.rolesusuario.permissions import role_required, ROLE_ADMIN_NAME, ROLE_VENDEDOR_NAME
from smartsales.gestionproducto.storage import public_url
from .serializers import ProductoListadoQuerySerializer


class ListadoProductosView(APIView):
    """
    Vista para listar TODOS los productos del sistema (sin restricción de vendedor).
    Incluye búsqueda, filtros dinámicos y paginación.
    Accesible para todos los usuarios autenticados (sin restricción de roles).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Validar parámetros de query
        qs = ProductoListadoQuerySerializer(data=request.query_params)
        qs.is_valid(raise_exception=True)
        
        filters = qs.validated_data
        q = filters.get("q", "").strip()
        marca_id = filters.get("marca_id")
        tipo_id = filters.get("tipoproducto_id")
        min_precio = filters.get("min_precio")
        max_precio = filters.get("max_precio")
        min_stock = filters.get("min_stock")
        max_stock = filters.get("max_stock")
        page = filters.get("page", 1)
        page_size = filters.get("page_size", 20)

        # Construir condiciones WHERE dinámicamente
        conditions = []
        params = []

        if q:
            conditions.append("LOWER(p.nombre) LIKE LOWER(%s)")
            params.append(f"%{q}%")
        
        if marca_id is not None:
            conditions.append("p.marca_id = %s")
            params.append(marca_id)
        
        if tipo_id is not None:
            conditions.append("p.tipoproducto_id = %s")
            params.append(tipo_id)
        
        if min_precio is not None:
            conditions.append("p.precio >= %s")
            params.append(min_precio)
        
        if max_precio is not None:
            conditions.append("p.precio <= %s")
            params.append(max_precio)
        
        if min_stock is not None:
            conditions.append("p.stock >= %s")
            params.append(min_stock)
        
        if max_stock is not None:
            conditions.append("p.stock <= %s")
            params.append(max_stock)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Consulta para contar total de registros
        count_query = f"""
            SELECT COUNT(*)
            FROM producto p
            WHERE {where_clause}
        """
        total_count = execute_query_with_retry(count_query, params, fetch_one=True)[0]

        # Calcular offset para paginación
        offset = (page - 1) * page_size

        # Consulta principal con JOIN para obtener nombres de marca, tipo y vendedor
        main_query = f"""
            SELECT 
                p.id,
                p.nombre,
                p.precio,
                p.stock,
                p.tiempogarantia,
                p.imagen_key,
                p.marca_id,
                m.nombre AS marca_nombre,
                p.tipoproducto_id,
                t.nombre AS tipoproducto_nombre,
                p.id_vendedor,
                u.nombre AS vendedor_nombre,
                u.correo AS vendedor_correo
            FROM producto p
            INNER JOIN marca m ON p.marca_id = m.id
            INNER JOIN tipoproducto t ON p.tipoproducto_id = t.id
            INNER JOIN usuario u ON p.id_vendedor = u.id
            WHERE {where_clause}
            ORDER BY p.id DESC
            LIMIT %s OFFSET %s
        """
        
        params_with_pagination = params + [page_size, offset]
        rows = execute_query_with_retry(main_query, params_with_pagination, fetch_all=True)

        # Formatear resultados
        productos = []
        for row in rows:
            imagen_url = public_url(row[5]) if row[5] else None
            productos.append({
                "id": row[0],
                "nombre": row[1],
                "precio": float(row[2]),
                "stock": row[3],
                "tiempogarantia": row[4],
                "imagen_url": imagen_url,
                "marca": {
                    "id": row[6],
                    "nombre": row[7]
                },
                "tipoproducto": {
                    "id": row[8],
                    "nombre": row[9]
                },
                "vendedor": {
                    "id": str(row[10]),
                    "nombre": row[11],
                    "correo": row[12]
                }
            })

        return Response({
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size,
            "results": productos
        })


class FiltrosDisponiblesView(APIView):
    """
    Vista para obtener las opciones dinámicas de filtros (marcas y tipos de producto).
    Accesible para todos los usuarios autenticados (sin restricción de roles).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Obtener todas las marcas
        marcas_rows = execute_query_with_retry(
            "SELECT id, nombre FROM marca ORDER BY nombre ASC",
            fetch_all=True
        )
        marcas = [{"id": row[0], "nombre": row[1]} for row in marcas_rows]

        # Obtener todos los tipos de producto
        tipos_rows = execute_query_with_retry(
            "SELECT id, nombre FROM tipoproducto ORDER BY nombre ASC",
            fetch_all=True
        )
        tipos = [{"id": row[0], "nombre": row[1]} for row in tipos_rows]

        return Response({
            "marcas": marcas,
            "tipos": tipos
        })