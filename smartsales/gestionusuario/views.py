import os
import requests
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import connection, transaction

from smartsales.db_utils import execute_query_with_retry, db_retry
from smartsales.rolesusuario.permissions import IsAdminRole
# Reutilizamos los valores y la excepción del módulo authsupabase, sin modificarlo
from smartsales.authsupabase.api import AUTH_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_ANON_KEY, SupabaseError

from .serializers import (
    UsuarioItemSerializer,
    UsuarioListQuerySerializer,
    UsuarioPerfilUpdateSerializer,
    UsuarioRolesPutSerializer,
    UsuarioRolAddSerializer,
)

# ---------- Helpers ----------

def _fetch_user_with_roles(user_id):
    with connection.cursor() as cur:
        cur.execute("SELECT u.id, u.nombre, u.telefono, u.correo FROM usuario u WHERE u.id=%s", [user_id])
        u = cur.fetchone()
    if not u:
        return None
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
        roles = cur.fetchall()
    return {
        "id": u[0], "nombre": u[1], "telefono": u[2], "correo": u[3],
        "roles_ids": [r[0] for r in roles], "roles": [r[1] for r in roles],
    }

def _delete_user_in_supabase_auth(user_id: str):
    """
    Elimina al usuario en Supabase Auth via Admin API.
    Requiere SUPABASE_SERVICE_ROLE_KEY.
    """
    url = f"{AUTH_URL}/admin/users/{user_id}"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }
    r = requests.delete(url, headers=headers, timeout=20)
    if r.status_code not in (200, 204):
        raise SupabaseError(f"delete_user_admin error {r.status_code}: {r.text}")

# ---------- Vistas ----------

class UsuariosListView(APIView):
    """
    GET /gestionusuario/usuarios?search=&limit=50&offset=0
    """
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        q = UsuarioListQuerySerializer(data=request.query_params)
        q.is_valid(raise_exception=True)
        search = (q.validated_data.get("search") or "").strip()
        limit = q.validated_data.get("limit") or 50
        offset = q.validated_data.get("offset") or 0

        params, where = [], ""
        if search:
            where = "WHERE lower(u.correo) LIKE %s OR lower(u.nombre) LIKE %s"
            s = f"%{search.lower()}%"
            params.extend([s, s])

        with connection.cursor() as cur:
            cur.execute(
                f"""
                SELECT u.id, u.nombre, u.telefono, u.correo
                FROM usuario u
                {where}
                ORDER BY lower(u.correo)
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            rows = cur.fetchall()

        result = []
        for (uid, nombre, telefono, correo) in rows:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT r.id, r.nombre
                    FROM roles r
                    JOIN rolesusuario ru ON ru.rol_id = r.id
                    WHERE ru.usuario_id = %s
                    ORDER BY r.id
                    """,
                    [uid],
                )
                roles = cur.fetchall()
            result.append({
                "id": uid, "correo": correo, "nombre": nombre, "telefono": telefono,
                "roles_ids": [r[0] for r in roles], "roles": [r[1] for r in roles],
            })
        return Response([UsuarioItemSerializer(x).data for x in result], status=200)

class UsuarioPerfilUpdateView(APIView):
    """
    PATCH /gestionusuario/usuarios/<uuid:user_id>/perfil
    """
    permission_classes = [IsAuthenticated, IsAdminRole]

    @db_retry(max_attempts=3, delay=0.5)
    @transaction.atomic
    def patch(self, request, user_id):
        s = UsuarioPerfilUpdateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        nombre = s.validated_data.get("nombre", None)
        telefono = s.validated_data.get("telefono", None)

        if nombre is None and telefono is None:
            return Response({"detail": "Nada para actualizar."}, status=400)

        sets, params = [], []
        if nombre is not None:
            sets.append("nombre=%s"); params.append(nombre.strip())
        if telefono is not None:
            tel = telefono.strip() or None
            sets.append("telefono=%s"); params.append(tel)
        params.append(user_id)

        with connection.cursor() as cur:
            cur.execute(f"UPDATE usuario SET {', '.join(sets)} WHERE id=%s", params)
            if cur.rowcount == 0:
                return Response({"detail": "Usuario no encontrado."}, status=404)

        data = _fetch_user_with_roles(user_id)
        return Response(UsuarioItemSerializer(data).data, status=200)

class UsuarioRolesView(APIView):
    """
    PUT  /gestionusuario/usuarios/<uuid:user_id>/roles  -> reemplaza set completo
    POST /gestionusuario/usuarios/<uuid:user_id>/roles  -> agrega un rol
    """
    permission_classes = [IsAuthenticated, IsAdminRole]

    @db_retry(max_attempts=3, delay=0.5)
    @transaction.atomic
    def put(self, request, user_id):
        s = UsuarioRolesPutSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        roles_ids = s.validated_data["roles_ids"]

        if roles_ids:
            with connection.cursor() as cur:
                cur.execute("SELECT id FROM roles WHERE id=ANY(%s)", [roles_ids])
                existentes = {r[0] for r in cur.fetchall()}
            desconocidos = [r for r in roles_ids if r not in existentes]
            if desconocidos:
                return Response({"detail": f"Roles inexistentes: {desconocidos}"}, status=400)

        with connection.cursor() as cur:
            cur.execute("DELETE FROM rolesusuario WHERE usuario_id=%s", [user_id])

        if roles_ids:
            values = [(user_id, rid) for rid in roles_ids]
            with connection.cursor() as cur:
                args = ",".join(["(%s,%s)"] * len(values))
                flat = []
                for a, b in values: flat.extend([a, b])
                cur.execute(
                    f"INSERT INTO rolesusuario (usuario_id, rol_id) VALUES {args} ON CONFLICT DO NOTHING",
                    flat
                )

        data = _fetch_user_with_roles(user_id)
        if not data:
            return Response({"detail": "Usuario no encontrado."}, status=404)
        return Response(UsuarioItemSerializer(data).data, status=200)

    @db_retry(max_attempts=3, delay=0.5)
    @transaction.atomic
    def post(self, request, user_id):
        s = UsuarioRolAddSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        rol_id = s.validated_data["rol_id"]

        with connection.cursor() as cur:
            cur.execute("SELECT 1 FROM roles WHERE id=%s", [rol_id])
            if not cur.fetchone():
                return Response({"detail": "Rol inexistente."}, status=400)

        with connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO rolesusuario (usuario_id, rol_id)
                VALUES (%s, %s)
                ON CONFLICT (usuario_id, rol_id) DO NOTHING
                """,
                [user_id, rol_id],
            )

        data = _fetch_user_with_roles(user_id)
        if not data:
            return Response({"detail": "Usuario no encontrado."}, status=404)
        return Response(UsuarioItemSerializer(data).data, status=201)

class UsuarioRolDeleteView(APIView):
    """
    DELETE /gestionusuario/usuarios/<uuid:user_id>/roles/<int:rol_id>
    """
    permission_classes = [IsAuthenticated, IsAdminRole]

    @db_retry(max_attempts=3, delay=0.5)
    @transaction.atomic
    def delete(self, request, user_id, rol_id: int):
        with connection.cursor() as cur:
            cur.execute(
                "DELETE FROM rolesusuario WHERE usuario_id=%s AND rol_id=%s",
                [user_id, rol_id]
            )
        data = _fetch_user_with_roles(user_id)
        if not data:
            return Response({"detail": "Usuario no encontrado."}, status=404)
        return Response(UsuarioItemSerializer(data).data, status=200)

class UsuarioDeleteView(APIView):
    """
    DELETE /gestionusuario/usuarios/<uuid:user_id>
    Borra en Supabase Auth y luego en DB local.
    Nota: impedimos que un admin se auto-elimine.
    """
    permission_classes = [IsAuthenticated, IsAdminRole]

    @db_retry(max_attempts=3, delay=0.5)
    @transaction.atomic
    def delete(self, request, user_id):
        if str(request.user.id) == str(user_id):
            return Response({"detail": "No puedes eliminar tu propio usuario."}, status=400)

        # 1) Eliminar en Supabase Auth (Admin API)
        try:
            _delete_user_in_supabase_auth(str(user_id))
        except SupabaseError as e:
            return Response({"detail": f"Error en Supabase Auth: {e}"}, status=502)

        # 2) Eliminar en DB (respetará FKs; CASCADE donde aplique)
        with connection.cursor() as cur:
            cur.execute("DELETE FROM usuario WHERE id=%s", [user_id])
            if cur.rowcount == 0:
                # Si ya no existe en DB, igual devolvemos 204
                return Response(status=204)

        return Response(status=204)
