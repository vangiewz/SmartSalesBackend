from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from smartsales.db_utils import execute_query_with_retry
from .permissions import (
    ROLE_ADMIN_ID, ROLE_ADMIN_NAME,
    ROLE_VENDEDOR_NAME, ROLE_ANALISTA_NAME, ROLE_USUARIO_NAME,
    user_has_role,
)
from .serializers import (
    MisRolesResponseSerializer, CheckRoleQuerySerializer, CheckRoleResponseSerializer
)

class MisRolesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        uid = request.user.id
        row = execute_query_with_retry(
            "SELECT u.id, u.nombre, u.telefono, u.correo FROM usuario u WHERE u.id=%s",
            [uid],
            fetch_one=True
        )
        if not row:
            return Response({"detail": "No existe perfil en 'usuario'."}, status=404)

        user_id, nombre, telefono, correo = row

        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT r.id, r.nombre
                FROM roles r
                JOIN rolesusuario ru ON ru.rol_id = r.id
                WHERE ru.usuario_id = %s
                ORDER BY r.id
                """,
                [user_id],
            )
            data = cur.fetchall()

        roles_ids = [r[0] for r in data]
        roles     = [r[1] for r in data]

        payload = {
            "user_id": user_id,
            "correo": correo,
            "nombre": nombre,
            "telefono": telefono,
            "roles": roles,
            "roles_ids": roles_ids,
            "is_admin":    user_has_role(user_id, ROLE_ADMIN_ID) or user_has_role(user_id, ROLE_ADMIN_NAME),
            "is_vendedor": user_has_role(user_id, ROLE_VENDEDOR_NAME),
            "is_analista": user_has_role(user_id, ROLE_ANALISTA_NAME),
            "is_usuario":  user_has_role(user_id, ROLE_USUARIO_NAME),
        }
        return Response(MisRolesResponseSerializer(payload).data)

class CheckRoleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        q = CheckRoleQuerySerializer(data=request.query_params)
        q.is_valid(raise_exception=True)
        role_id = q.validated_data.get("role_id")
        role_name = q.validated_data.get("role_name")

        if not role_id and not role_name:
            return Response({"detail": "Debe enviar role_id o role_name."}, status=400)

        if role_name and not role_id:
            with connection.cursor() as cur:
                cur.execute("SELECT id FROM roles WHERE lower(nombre)=lower(%s) LIMIT 1", [role_name])
                r = cur.fetchone()
                role_id = r[0] if r else None
                if not role_id:
                    return Response({"detail": "Rol no encontrado."}, status=404)
        elif role_id and not role_name:
            with connection.cursor() as cur:
                cur.execute("SELECT nombre FROM roles WHERE id=%s", [role_id])
                r = cur.fetchone()
                role_name = r[0] if r else None

        has = user_has_role(request.user.id, role_id if role_id else role_name)
        return Response(CheckRoleResponseSerializer({
            "has_role": has, "role_id": role_id, "role_name": role_name
        }).data)
