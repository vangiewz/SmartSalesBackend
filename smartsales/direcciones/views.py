from django.db import connection, transaction
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .serializers import DireccionSerializer


class GestionDireccionesView(APIView):
    """
    Vista para gestionar las direcciones del usuario autenticado.
    Soporta operaciones CRUD completas.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Listar todas las direcciones del usuario autenticado"""
        usuario_id = request.user.id
        
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, direccion FROM direcciones WHERE usuario_id = %s ORDER BY id DESC",
                [usuario_id]
            )
            rows = cursor.fetchall()
        
        direcciones = [{"id": row[0], "direccion": row[1]} for row in rows]
        return Response(direcciones)

    def post(self, request):
        """Crear una nueva dirección para el usuario autenticado"""
        serializer = DireccionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        usuario_id = request.user.id
        direccion = serializer.validated_data["direccion"]
        
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO direcciones (usuario_id, direccion)
                    VALUES (%s, %s)
                    RETURNING id, direccion
                    """,
                    [usuario_id, direccion]
                )
                row = cursor.fetchone()
        
        return Response(
            {"id": row[0], "direccion": row[1]},
            status=status.HTTP_201_CREATED
        )

    def put(self, request, id):
        """Actualizar una dirección existente del usuario autenticado"""
        serializer = DireccionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        usuario_id = request.user.id
        direccion = serializer.validated_data["direccion"]
        
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE direcciones
                    SET direccion = %s
                    WHERE id = %s AND usuario_id = %s
                    RETURNING id, direccion
                    """,
                    [direccion, id, usuario_id]
                )
                row = cursor.fetchone()
        
        if not row:
            return Response(
                {"detail": "Dirección no encontrada."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response({"id": row[0], "direccion": row[1]})

    def delete(self, request, id):
        """Eliminar una dirección del usuario autenticado"""
        usuario_id = request.user.id
        
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM direcciones WHERE id = %s AND usuario_id = %s",
                    [id, usuario_id]
                )
        
        return Response(status=status.HTTP_204_NO_CONTENT)
