from django.db import connection, IntegrityError
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from smartsales.rolesusuario.permissions import IsAdminRole
from .serializers import (
    TipoProductoSerializer,
    CrearTipoProductoSerializer,
    ActualizarTipoProductoSerializer,
    MarcaSerializer,
    CrearMarcaSerializer,
    ActualizarMarcaSerializer,
)


# ==================== GESTIÓN DE TIPOS DE PRODUCTO ====================

class ListarTiposProductoView(APIView):
    """
    Vista para listar todos los tipos de producto.
    Solo accesible por administradores.
    
    GET /api/gestion-catalogos/tipos-producto/
    """
    permission_classes = [IsAuthenticated, IsAdminRole]
    
    def get(self, request):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, nombre
                FROM tipoproducto
                ORDER BY nombre ASC
                """
            )
            rows = cursor.fetchall()
        
        tipos = [
            {'id': row[0], 'nombre': row[1]}
            for row in rows
        ]
        
        return Response(
            TipoProductoSerializer(tipos, many=True).data,
            status=status.HTTP_200_OK
        )


class CrearTipoProductoView(APIView):
    """
    Vista para crear un nuevo tipo de producto.
    Solo accesible por administradores.
    
    POST /api/gestion-catalogos/tipos-producto/
    Body: {"nombre": "Nuevo Tipo"}
    """
    permission_classes = [IsAuthenticated, IsAdminRole]
    
    def post(self, request):
        serializer = CrearTipoProductoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        nombre = serializer.validated_data['nombre'].strip()
        
        # Verificar si ya existe (case-insensitive gracias al índice único)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, nombre FROM tipoproducto WHERE LOWER(nombre) = LOWER(%s)",
                [nombre]
            )
            existente = cursor.fetchone()
            
            if existente:
                return Response(
                    {"detail": f"Ya existe un tipo de producto con el nombre '{existente[1]}'."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Crear tipo de producto
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO tipoproducto (nombre)
                    VALUES (%s)
                    RETURNING id, nombre
                    """,
                    [nombre]
                )
                row = cursor.fetchone()
            
            tipo_creado = {
                'id': row[0],
                'nombre': row[1]
            }
            
            return Response(
                TipoProductoSerializer(tipo_creado).data,
                status=status.HTTP_201_CREATED
            )
        
        except IntegrityError as e:
            return Response(
                {"detail": f"Error al crear el tipo de producto: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )


class ActualizarTipoProductoView(APIView):
    """
    Vista para actualizar un tipo de producto existente.
    Solo accesible por administradores.
    
    PUT /api/gestion-catalogos/tipos-producto/{id}/
    Body: {"nombre": "Nuevo Nombre"}
    """
    permission_classes = [IsAuthenticated, IsAdminRole]
    
    def put(self, request, tipo_id):
        serializer = ActualizarTipoProductoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        nuevo_nombre = serializer.validated_data['nombre'].strip()
        
        # Verificar que el tipo existe
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, nombre FROM tipoproducto WHERE id = %s",
                [tipo_id]
            )
            tipo_actual = cursor.fetchone()
        
        if not tipo_actual:
            return Response(
                {"detail": f"No se encontró el tipo de producto con ID {tipo_id}."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verificar si el nuevo nombre ya existe en otro tipo
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, nombre FROM tipoproducto 
                WHERE LOWER(nombre) = LOWER(%s) AND id != %s
                """,
                [nuevo_nombre, tipo_id]
            )
            conflicto = cursor.fetchone()
            
            if conflicto:
                return Response(
                    {"detail": f"Ya existe otro tipo de producto con el nombre '{conflicto[1]}'."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Actualizar
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE tipoproducto
                    SET nombre = %s
                    WHERE id = %s
                    RETURNING id, nombre
                    """,
                    [nuevo_nombre, tipo_id]
                )
                row = cursor.fetchone()
            
            tipo_actualizado = {
                'id': row[0],
                'nombre': row[1]
            }
            
            return Response(
                TipoProductoSerializer(tipo_actualizado).data,
                status=status.HTTP_200_OK
            )
        
        except IntegrityError as e:
            return Response(
                {"detail": f"Error al actualizar el tipo de producto: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )


class EliminarTipoProductoView(APIView):
    """
    Vista para eliminar un tipo de producto.
    Solo accesible por administradores.
    
    DELETE /api/gestion-catalogos/tipos-producto/{id}/
    """
    permission_classes = [IsAuthenticated, IsAdminRole]
    
    def delete(self, request, tipo_id):
        # Verificar que el tipo existe
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, nombre FROM tipoproducto WHERE id = %s",
                [tipo_id]
            )
            tipo = cursor.fetchone()
        
        if not tipo:
            return Response(
                {"detail": f"No se encontró el tipo de producto con ID {tipo_id}."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verificar si hay productos usando este tipo
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM producto WHERE tipoproducto_id = %s",
                [tipo_id]
            )
            count = cursor.fetchone()[0]
        
        if count > 0:
            return Response(
                {
                    "detail": f"No se puede eliminar el tipo '{tipo[1]}' porque tiene {count} producto(s) asociado(s). "
                             "Primero debes reasignar o eliminar esos productos."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Eliminar
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM tipoproducto WHERE id = %s",
                    [tipo_id]
                )
            
            return Response(
                {"detail": f"Tipo de producto '{tipo[1]}' eliminado exitosamente."},
                status=status.HTTP_200_OK
            )
        
        except IntegrityError as e:
            return Response(
                {"detail": f"Error al eliminar el tipo de producto: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )


# ==================== GESTIÓN DE MARCAS ====================

class ListarMarcasView(APIView):
    """
    Vista para listar todas las marcas.
    Solo accesible por administradores.
    
    GET /api/gestion-catalogos/marcas/
    """
    permission_classes = [IsAuthenticated, IsAdminRole]
    
    def get(self, request):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, nombre
                FROM marca
                ORDER BY nombre ASC
                """
            )
            rows = cursor.fetchall()
        
        marcas = [
            {'id': row[0], 'nombre': row[1]}
            for row in rows
        ]
        
        return Response(
            MarcaSerializer(marcas, many=True).data,
            status=status.HTTP_200_OK
        )


class CrearMarcaView(APIView):
    """
    Vista para crear una nueva marca.
    Solo accesible por administradores.
    
    POST /api/gestion-catalogos/marcas/
    Body: {"nombre": "Nueva Marca"}
    """
    permission_classes = [IsAuthenticated, IsAdminRole]
    
    def post(self, request):
        serializer = CrearMarcaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        nombre = serializer.validated_data['nombre'].strip()
        
        # Verificar si ya existe (case-insensitive gracias al índice único)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, nombre FROM marca WHERE LOWER(nombre) = LOWER(%s)",
                [nombre]
            )
            existente = cursor.fetchone()
            
            if existente:
                return Response(
                    {"detail": f"Ya existe una marca con el nombre '{existente[1]}'."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Crear marca
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO marca (nombre)
                    VALUES (%s)
                    RETURNING id, nombre
                    """,
                    [nombre]
                )
                row = cursor.fetchone()
            
            marca_creada = {
                'id': row[0],
                'nombre': row[1]
            }
            
            return Response(
                MarcaSerializer(marca_creada).data,
                status=status.HTTP_201_CREATED
            )
        
        except IntegrityError as e:
            return Response(
                {"detail": f"Error al crear la marca: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )


class ActualizarMarcaView(APIView):
    """
    Vista para actualizar una marca existente.
    Solo accesible por administradores.
    
    PUT /api/gestion-catalogos/marcas/{id}/
    Body: {"nombre": "Nuevo Nombre"}
    """
    permission_classes = [IsAuthenticated, IsAdminRole]
    
    def put(self, request, marca_id):
        serializer = ActualizarMarcaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        nuevo_nombre = serializer.validated_data['nombre'].strip()
        
        # Verificar que la marca existe
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, nombre FROM marca WHERE id = %s",
                [marca_id]
            )
            marca_actual = cursor.fetchone()
        
        if not marca_actual:
            return Response(
                {"detail": f"No se encontró la marca con ID {marca_id}."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verificar si el nuevo nombre ya existe en otra marca
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, nombre FROM marca 
                WHERE LOWER(nombre) = LOWER(%s) AND id != %s
                """,
                [nuevo_nombre, marca_id]
            )
            conflicto = cursor.fetchone()
            
            if conflicto:
                return Response(
                    {"detail": f"Ya existe otra marca con el nombre '{conflicto[1]}'."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Actualizar
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE marca
                    SET nombre = %s
                    WHERE id = %s
                    RETURNING id, nombre
                    """,
                    [nuevo_nombre, marca_id]
                )
                row = cursor.fetchone()
            
            marca_actualizada = {
                'id': row[0],
                'nombre': row[1]
            }
            
            return Response(
                MarcaSerializer(marca_actualizada).data,
                status=status.HTTP_200_OK
            )
        
        except IntegrityError as e:
            return Response(
                {"detail": f"Error al actualizar la marca: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )


class EliminarMarcaView(APIView):
    """
    Vista para eliminar una marca.
    Solo accesible por administradores.
    
    DELETE /api/gestion-catalogos/marcas/{id}/
    """
    permission_classes = [IsAuthenticated, IsAdminRole]
    
    def delete(self, request, marca_id):
        # Verificar que la marca existe
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, nombre FROM marca WHERE id = %s",
                [marca_id]
            )
            marca = cursor.fetchone()
        
        if not marca:
            return Response(
                {"detail": f"No se encontró la marca con ID {marca_id}."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verificar si hay productos usando esta marca
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM producto WHERE marca_id = %s",
                [marca_id]
            )
            count = cursor.fetchone()[0]
        
        if count > 0:
            return Response(
                {
                    "detail": f"No se puede eliminar la marca '{marca[1]}' porque tiene {count} producto(s) asociado(s). "
                             "Primero debes reasignar o eliminar esos productos."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Eliminar
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM marca WHERE id = %s",
                    [marca_id]
                )
            
            return Response(
                {"detail": f"Marca '{marca[1]}' eliminada exitosamente."},
                status=status.HTTP_200_OK
            )
        
        except IntegrityError as e:
            return Response(
                {"detail": f"Error al eliminar la marca: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
