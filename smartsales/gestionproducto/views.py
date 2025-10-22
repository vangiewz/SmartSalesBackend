from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from smartsales.db_utils import execute_query_with_retry
from smartsales.rolesusuario.permissions import (
    role_required, ROLE_ADMIN_NAME, ROLE_VENDEDOR_NAME, user_has_role
)
from .serializers import (
    ProductoCreateSerializer, ProductoUpdateSerializer, ProductoQuerySerializer
)
from .storage import upload_image, delete_image_if_exists, public_url

# ---------- Helpers ----------

def _is_admin(user_id) -> bool:
    return user_has_role(user_id, ROLE_ADMIN_NAME)

def _can_touch_product(user_id, product_row) -> bool:
    """
    product_row = (id, id_vendedor, imagen_key, ...)
    Admin: True
    Vendedor: True si product_row.id_vendedor == user_id
    """
    if _is_admin(user_id):
        return True
    return product_row and str(product_row[1]) == str(user_id)

def _get_product_or_404(prod_id: int):
    return execute_query_with_retry(
        """
        SELECT id, id_vendedor, imagen_key, nombre, precio, stock, tiempogarantia,
               marca_id, tipoproducto_id
        FROM producto
        WHERE id=%s
        """,
        [prod_id],
        fetch_one=True
    )

def _row_to_payload(row):
    pid, id_vend, img_key, nombre, precio, stock, tg, marca_id, tipo_id = row
    return {
        "id": pid,
        "id_vendedor": str(id_vend),
        "imagen_key": img_key,
        "imagen_url": public_url(img_key),
        "nombre": nombre,
        "precio": float(precio),
        "stock": int(stock),
        "tiempogarantia": int(tg),
        "marca_id": int(marca_id),
        "tipoproducto_id": int(tipo_id),
    }

# ---------- Catálogos ----------

class MarcaListView(APIView):
    permission_classes = [IsAuthenticated, role_required(ROLE_ADMIN_NAME, ROLE_VENDEDOR_NAME)]
    def get(self, request):
        rows = execute_query_with_retry(
            "SELECT id, nombre FROM marca ORDER BY nombre ASC",
            fetch_all=True
        )
        return Response([{"id": r[0], "nombre": r[1]} for r in rows])

class TipoProductoListView(APIView):
    permission_classes = [IsAuthenticated, role_required(ROLE_ADMIN_NAME, ROLE_VENDEDOR_NAME)]
    def get(self, request):
        rows = execute_query_with_retry(
            "SELECT id, nombre FROM tipoproducto ORDER BY nombre ASC",
            fetch_all=True
        )
        return Response([{"id": r[0], "nombre": r[1]} for r in rows])

# ---------- Listar / Crear ----------

class ProductoListCreateView(APIView):
    permission_classes = [IsAuthenticated, role_required(ROLE_ADMIN_NAME, ROLE_VENDEDOR_NAME)]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        uid = request.user.id
        qser = ProductoQuerySerializer(data=request.query_params)
        qser.is_valid(raise_exception=True)

        q = qser.validated_data.get("q")
        marca_id = qser.validated_data.get("marca_id")
        tipo_id = qser.validated_data.get("tipoproducto_id")
        min_precio = qser.validated_data.get("min_precio")
        max_precio = qser.validated_data.get("max_precio")
        page = qser.validated_data.get("page") or 1
        page_size = qser.validated_data.get("page_size") or 20
        offset = (page - 1) * page_size

        filters = []
        params = []

        if not _is_admin(uid):
            filters.append("p.id_vendedor = %s")
            params.append(uid)

        if q:
            filters.append("lower(p.nombre) LIKE lower(%s)")
            params.append(f"%{q}%")
        if marca_id:
            filters.append("p.marca_id = %s")
            params.append(marca_id)
        if tipo_id:
            filters.append("p.tipoproducto_id = %s")
            params.append(tipo_id)
        if min_precio is not None:
            filters.append("p.precio >= %s")
            params.append(min_precio)
        if max_precio is not None:
            filters.append("p.precio <= %s")
            params.append(max_precio)

        where = ("WHERE " + " AND ".join(filters)) if filters else ""

        count_row = execute_query_with_retry(
            f"SELECT COUNT(*) FROM producto p {where}",
            params,
            fetch_one=True
        )
        total = int(count_row[0]) if count_row else 0

        rows = execute_query_with_retry(
            f"""
            SELECT p.id, p.id_vendedor, p.imagen_key, p.nombre, p.precio, p.stock,
                   p.tiempogarantia, p.marca_id, p.tipoproducto_id
            FROM producto p
            {where}
            ORDER BY p.id DESC
            LIMIT %s OFFSET %s
            """,
            params + [page_size, offset],
            fetch_all=True
        )
        data = [_row_to_payload(r) for r in rows]
        return Response({"count": total, "page": page, "page_size": page_size, "results": data})

    def post(self, request):
        uid = request.user.id
        
        # Validar datos del formulario
        s = ProductoCreateSerializer(data=request.data)
        if not s.is_valid():
            return Response({"detail": "Datos inválidos", "errors": s.errors}, status=400)

        # imagen obligatoria
        fileobj = request.FILES.get("imagen")
        if not fileobj:
            return Response({"detail": "La imagen es obligatoria."}, status=400)
        
        # Validar que marca_id y tipoproducto_id existan
        marca_id = s.validated_data["marca_id"]
        tipo_id = s.validated_data["tipoproducto_id"]
        
        marca_exists = execute_query_with_retry(
            "SELECT 1 FROM marca WHERE id=%s", [marca_id], fetch_one=True
        )
        if not marca_exists:
            return Response({"detail": f"La marca con ID {marca_id} no existe."}, status=400)
        
        tipo_exists = execute_query_with_retry(
            "SELECT 1 FROM tipoproducto WHERE id=%s", [tipo_id], fetch_one=True
        )
        if not tipo_exists:
            return Response({"detail": f"El tipo de producto con ID {tipo_id} no existe."}, status=400)

        # 1. Primero insertar el producto SIN imagen para obtener el ID
        row = execute_query_with_retry(
            """
            INSERT INTO producto (nombre, precio, tiempogarantia, stock, marca_id, tipoproducto_id, id_vendedor)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, id_vendedor, imagen_key, nombre, precio, stock, tiempogarantia, marca_id, tipoproducto_id
            """,
            [
                s.validated_data["nombre"].strip(),
                s.validated_data["precio"],
                s.validated_data["tiempogarantia"],
                s.validated_data["stock"],
                s.validated_data["marca_id"],
                s.validated_data["tipoproducto_id"],
                uid,
            ],
            fetch_one=True
        )
        
        producto_id = row[0]
        
        try:
            # 2. Subir imagen a Supabase Storage
            imagen_key = upload_image(fileobj.read(), fileobj.name, str(uid))
            
            # 3. Actualizar el producto con la imagen_key
            execute_query_with_retry(
                "UPDATE producto SET imagen_key=%s WHERE id=%s",
                [imagen_key, producto_id]
            )
            
            # 4. Obtener el producto actualizado
            row = execute_query_with_retry(
                """
                SELECT id, id_vendedor, imagen_key, nombre, precio, stock, 
                       tiempogarantia, marca_id, tipoproducto_id
                FROM producto WHERE id=%s
                """,
                [producto_id],
                fetch_one=True
            )
            
            return Response(_row_to_payload(row), status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # Si falla la subida de imagen o la actualización, borrar el producto creado
            execute_query_with_retry("DELETE FROM producto WHERE id=%s", [producto_id])
            return Response(
                {"detail": f"Error al subir la imagen: {str(e)}"},
                status=500
            )

# ---------- Detalle / Update / Delete ----------

class ProductoDetailView(APIView):
    permission_classes = [IsAuthenticated, role_required(ROLE_ADMIN_NAME, ROLE_VENDEDOR_NAME)]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request, pk: int):
        row = _get_product_or_404(pk)
        if not row:
            return Response({"detail": "Producto no encontrado."}, status=404)
        if not _can_touch_product(request.user.id, row):
            return Response({"detail": "No autorizado."}, status=403)
        return Response(_row_to_payload(row))

    def patch(self, request, pk: int):
        uid = request.user.id
        row = _get_product_or_404(pk)
        if not row:
            return Response({"detail": "Producto no encontrado."}, status=404)
        if not _can_touch_product(uid, row):
            return Response({"detail": "No autorizado."}, status=403)

        s = ProductoUpdateSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)

        sets, params = [], []
        mapping = {
            "nombre": "nombre",
            "precio": "precio",
            "tiempogarantia": "tiempogarantia",
            "stock": "stock",
            "marca_id": "marca_id",
            "tipoproducto_id": "tipoproducto_id",
        }
        for k, col in mapping.items():
            if k in s.validated_data:
                sets.append(f"{col}=%s")
                params.append(s.validated_data[k])

        # imagen opcional en update
        new_key = None
        fileobj = request.FILES.get("imagen")
        if fileobj:
            new_key = upload_image(fileobj.read(), fileobj.name, str(uid))
            sets.append("imagen_key=%s")
            params.append(new_key)

        if sets:
            params.append(pk)
            execute_query_with_retry(
                f"UPDATE producto SET {', '.join(sets)} WHERE id=%s",
                params
            )

        # borrar imagen anterior si se reemplazó
        old_key = row[2]
        if new_key and old_key and old_key != new_key:
            delete_image_if_exists(old_key)

        row2 = _get_product_or_404(pk)
        return Response(_row_to_payload(row2))

    def delete(self, request, pk: int):
        uid = request.user.id
        row = _get_product_or_404(pk)
        if not row:
            return Response({"detail": "Producto no encontrado."}, status=404)
        if not _can_touch_product(uid, row):
            return Response({"detail": "No autorizado."}, status=403)

        imagen_key = row[2]
        try:
            execute_query_with_retry("DELETE FROM producto WHERE id=%s", [pk])
        except Exception:
            return Response(
                {"detail": "No se puede eliminar: el producto tiene ventas asociadas."},
                status=409
            )

        delete_image_if_exists(imagen_key)
        return Response(status=204)
