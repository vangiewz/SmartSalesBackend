from django.db import connection, transaction
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from .serializers import RegisterSerializer, LoginSerializer, UsuarioMeSerializer
from .authsupabase.api import create_user_admin, sign_in_password, SupabaseError

class RegisterView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        s = RegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        email = s.validated_data["email"].strip().lower()
        password = s.validated_data["password"]
        nombre = s.validated_data["nombre"].strip()
        telefono = (s.validated_data.get("telefono") or "").strip() or None

        # 1) Crear en Supabase (admin)
        try:
            supa_user = create_user_admin(email, password, {"nombre": nombre, "telefono": telefono})
        except SupabaseError as e:
            return Response({"detail": str(e)}, status=400)

        user_id = supa_user.get("id")
        if not user_id:
            return Response({"detail": "No se recibió 'id' del usuario de Supabase."}, status=500)

        # 2) Insertar perfil
        with connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO usuario (id, nombre, telefono, correo)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                [user_id, nombre, telefono, email],
            )

        # 3) Rol por defecto (id=1 => 'Usuario')
        with connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO rolesusuario (usuario_id, rol_id)
                VALUES (%s, %s)
                ON CONFLICT (usuario_id, rol_id) DO NOTHING
                """,
                [user_id, 1],
            )

        # 4) Autologin
        try:
            token_data = sign_in_password(email, password)
        except SupabaseError as e:
            return Response({"detail": f"Registrado, pero fallo login: {e}"}, status=201)

        perfil = {
            "id": user_id,
            "correo": email,
            "nombre": nombre,
            "telefono": telefono,
            "roles": ["Usuario"],
        }

        return Response({
            "user": perfil,
            "tokens": {
                "access": token_data.get("access_token"),
                "refresh": token_data.get("refresh_token"),
                "token_type": token_data.get("token_type", "bearer"),
                "expires_in": token_data.get("expires_in"),
            },
        }, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        s = LoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        email = s.validated_data["email"].strip().lower()
        password = s.validated_data["password"]

        # 1) Tokens desde Supabase
        try:
            token_data = sign_in_password(email, password)
        except SupabaseError:
            return Response({"detail": "Credenciales inválidas."}, status=401)

        # 2) Perfil + roles
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT u.id, u.nombre, u.telefono, u.correo
                FROM usuario u
                WHERE lower(u.correo) = lower(%s)
                """,
                [email],
            )
            row = cur.fetchone()

        if row:
            user_id, nombre, telefono, correo = row
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT r.nombre
                    FROM roles r
                    JOIN rolesusuario ru ON ru.rol_id = r.id
                    WHERE ru.usuario_id = %s
                    """,
                    [user_id],
                )
                roles = [r[0] for r in cur.fetchall()]
        else:
            user_id, nombre, telefono, correo, roles = None, None, None, email, []

        perfil = {
            "id": user_id,
            "correo": correo,
            "nombre": nombre,
            "telefono": telefono,
            "roles": roles,
        }

        return Response({
            "user": perfil,
            "tokens": {
                "access": token_data.get("access_token"),
                "refresh": token_data.get("refresh_token"),
                "token_type": token_data.get("token_type", "bearer"),
                "expires_in": token_data.get("expires_in"),
            },
        })

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        uid = request.user.id  # viene del JWT de Supabase
        if not uid:
            return Response({"detail": "Token sin 'sub'."}, status=400)

        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT u.id, u.nombre, u.telefono, u.correo
                FROM usuario u
                WHERE u.id = %s
                """,
                [uid],
            )
            row = cur.fetchone()

        if not row:
            return Response({"detail": "No existe perfil en 'usuario'."}, status=404)

        user_id, nombre, telefono, correo = row

        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT r.nombre
                FROM roles r
                JOIN rolesusuario ru ON ru.rol_id = r.id
                WHERE ru.usuario_id = %s
                """,
                [user_id],
            )
            roles = [r[0] for r in cur.fetchall()]

        data = {
            "id": user_id,
            "nombre": nombre,
            "telefono": telefono,
            "correo": correo,
            "roles": roles,
        }
        return Response(UsuarioMeSerializer(data).data)
