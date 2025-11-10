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
    UsuarioChangePasswordSerializer,   # 👈 NUEVO
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


# ============== NUEVO: MI PERFIL (usuario logueado) ==============

class MiPerfilView(APIView):
    """
    GET   /gestionusuario/mi-perfil/
    PATCH /gestionusuario/mi-perfil/
    Permite que el propio usuario vea y edite su perfil (nombre, teléfono).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = str(request.user.id)
        data = _fetch_user_with_roles(user_id)
        if not data:
            return Response({"detail": "Usuario no encontrado."}, status=404)
        return Response(UsuarioItemSerializer(data).data, status=200)

    @db_retry(max_attempts=3, delay=0.5)
    @transaction.atomic
    def patch(self, request):
        user_id = str(request.user.id)

        s = UsuarioPerfilUpdateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        nombre = s.validated_data.get("nombre", None)
        telefono = s.validated_data.get("telefono", None)

        if nombre is None and telefono is None:
            return Response({"detail": "Nada para actualizar."}, status=400)

        sets, params = [], []
        if nombre is not None:
            sets.append("nombre=%s")
            params.append(nombre.strip())
        if telefono is not None:
            tel = telefono.strip() or None
            sets.append("telefono=%s")
            params.append(tel)
        params.append(user_id)

        with connection.cursor() as cur:
            cur.execute(f"UPDATE usuario SET {', '.join(sets)} WHERE id=%s", params)
            if cur.rowcount == 0:
                return Response({"detail": "Usuario no encontrado."}, status=404)

        data = _fetch_user_with_roles(user_id)
        return Response(UsuarioItemSerializer(data).data, status=200)

class UsuarioChangePasswordView(APIView):
    """
    POST /gestionusuario/mi-perfil/cambiar-password/

    Requiere:
    - current_password
    - new_password
    - new_password_confirm

    Flujo:
    1) Busca el correo del usuario en tabla `usuario`.
    2) Llama a Supabase Auth /token?grant_type=password para verificar current_password.
    3) Si es correcto, con ese access_token hace PATCH /user para actualizar password.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        s = UsuarioChangePasswordSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        current_password = s.validated_data["current_password"]
        new_password = s.validated_data["new_password"]

        if not AUTH_URL or not SUPABASE_ANON_KEY:
            return Response(
                {"detail": "Faltan variables AUTH_URL o SUPABASE_ANON_KEY."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 1) Obtener correo del usuario desde tu tabla local `usuario`
        user_id = str(request.user.id)
        with connection.cursor() as cur:
            cur.execute("SELECT correo FROM usuario WHERE id=%s", [user_id])
            row = cur.fetchone()

        if not row:
            return Response(
                {"detail": "Usuario no encontrado en la base de datos."},
                status=status.HTTP_404_NOT_FOUND,
            )

        correo = row[0]

        # 2) Verificar contraseña actual con Supabase (/token?grant_type=password)
        try:
            r_login = requests.post(
                f"{AUTH_URL}/token?grant_type=password",
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Content-Type": "application/json",
                },
                json={"email": correo, "password": current_password},
                timeout=20,
            )
        except requests.RequestException as e:
            return Response(
                {"detail": f"Error comunicando con Supabase (login): {e}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if r_login.status_code >= 400:
            # Normalmente, si la contraseña está mal, Supabase devuelve:
            # {"error":"invalid_grant","error_description":"Invalid login credentials"}
            try:
                body = r_login.json()
            except ValueError:
                body = {"raw": r_login.text}

            return Response(
                {
                    "detail": "La contraseña actual es incorrecta.",
                    "supabase_error": body.get("error"),
                    "supabase_error_description": body.get("error_description"),
                    "supabase_status": r_login.status_code,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        login_data = r_login.json()
        access_token = login_data.get("access_token")
        if not access_token:
            return Response(
                {
                    "detail": (
                        "Supabase no devolvió access_token al verificar "
                        "la contraseña actual."
                    ),
                    "supabase_login_response": login_data,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3) Cambiar la contraseña llamando a /user con ese access_token
        try:
            # 👇 IMPORTANTE: usar PUT en vez de PATCH (405 = Method Not Allowed)
            r_change = requests.put(
                f"{AUTH_URL}/user",
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"password": new_password},
                timeout=20,
            )
        except requests.RequestException as e:
            return Response(
                {"detail": f"Error comunicando con Supabase (cambio de contraseña): {e}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if r_change.status_code >= 400:
            try:
                body = r_change.json()
            except ValueError:
                body = {"raw": r_change.text}
            return Response(
                {
                    "detail": "No se pudo actualizar la contraseña en Supabase.",
                    "supabase_status": r_change.status_code,
                    "supabase_response": body,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"detail": "Contraseña actualizada correctamente."},
            status=status.HTTP_200_OK,
        )

