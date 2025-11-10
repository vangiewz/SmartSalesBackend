from django.db import connection, transaction
from django.db.utils import OperationalError, InterfaceError, DatabaseError
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
import logging

from .serializers import RegisterSerializer, LoginSerializer, UsuarioMeSerializer
from .authsupabase.api import create_user_admin, sign_in_password, SupabaseError
from .db_utils import db_retry, execute_query_with_retry

logger = logging.getLogger(__name__)

class RegisterView(APIView):
    permission_classes = [AllowAny]

    @db_retry(max_attempts=3, delay=0.5)
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

MAX_INTENTOS = 3
BLOQUEO_MINUTOS = 15

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        s = LoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        email = s.validated_data["email"].strip().lower()
        password = s.validated_data["password"]
        now = timezone.now()

        # 1️⃣ Verificar si el usuario está bloqueado
        with connection.cursor() as cur:
            cur.execute("""
                SELECT intentos, bloqueado_hasta
                FROM login_bloqueo
                WHERE lower(email) = lower(%s)
            """, [email])
            row = cur.fetchone()

        if row:
            intentos, bloqueado_hasta = row
            if bloqueado_hasta and bloqueado_hasta > now:
                minutos = int((bloqueado_hasta - now).total_seconds() // 60) + 1
                return Response(
                    {"detail": f"Has excedido los intentos de acceso. Vuelve a intentarlo en {minutos} minuto(s)."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
        else:
            intentos = 0

        # 2️⃣ Intentar login normal (usa tu función actual sign_in_password)
        try:
            token_data = sign_in_password(email, password)
        except SupabaseError:
            token_data = None

        if not token_data:
            intentos += 1
            bloqueado_hasta = None
            if intentos >= MAX_INTENTOS:
                bloqueado_hasta = now + timedelta(minutes=BLOQUEO_MINUTOS)

            with connection.cursor() as cur:
                cur.execute("""
                    INSERT INTO login_bloqueo (email, intentos, bloqueado_hasta, actualizado_en)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (email)
                    DO UPDATE SET intentos=%s, bloqueado_hasta=%s, actualizado_en=%s
                """, [email, intentos, bloqueado_hasta, now, intentos, bloqueado_hasta, now])

            if intentos >= MAX_INTENTOS:
                return Response(
                    {"detail": f"Has fallado el inicio de sesión {MAX_INTENTOS} veces. Tu cuenta estará bloqueada durante {BLOQUEO_MINUTOS} minutos."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )

            return Response({"detail": "Correo o contraseña incorrectos."}, status=status.HTTP_400_BAD_REQUEST)

        # 3️⃣ Si login correcto → limpiar intentos
        with connection.cursor() as cur:
            cur.execute("DELETE FROM login_bloqueo WHERE lower(email) = lower(%s)", [email])

        # 4️⃣ Cargar perfil (copiado de tu código actual)
        with connection.cursor() as cur:
            cur.execute("""
                SELECT u.id, u.nombre, u.telefono, u.correo
                FROM usuario u
                WHERE lower(u.correo) = lower(%s)
            """, [email])
            row = cur.fetchone()

        if row:
            user_id, nombre, telefono, correo = row
            with connection.cursor() as cur:
                cur.execute("""
                    SELECT r.nombre
                    FROM roles r
                    JOIN rolesusuario ru ON ru.rol_id = r.id
                    WHERE ru.usuario_id = %s
                """, [user_id])
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
        }, status=status.HTTP_200_OK)
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @db_retry(max_attempts=3, delay=0.5)
    def get(self, request):
        uid = request.user.id  # viene del JWT de Supabase
        if not uid:
            return Response({"detail": "Token sin 'sub'."}, status=400)

        row = execute_query_with_retry(
            """
            SELECT u.id, u.nombre, u.telefono, u.correo
            FROM usuario u
            WHERE u.id = %s
            """,
            [uid],
            fetch_one=True
        )

        if not row:
            return Response({"detail": "No existe perfil en 'usuario'."}, status=404)

        user_id, nombre, telefono, correo = row

        roles_rows = execute_query_with_retry(
            """
            SELECT r.nombre
            FROM roles r
            JOIN rolesusuario ru ON ru.rol_id = r.id
            WHERE ru.usuario_id = %s
            """,
            [user_id],
            fetch_all=True
        )
        roles = [r[0] for r in roles_rows]

        data = {
            "id": user_id,
            "nombre": nombre,
            "telefono": telefono,
            "correo": correo,
            "roles": roles,
        }
        return Response(UsuarioMeSerializer(data).data)


class HealthCheckView(APIView):
    """
    Health check para mantener el servicio activo en Render free tier.
    También verifica que la conexión a la BD funcione correctamente.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            # Verificar conexión a BD
            row = execute_query_with_retry(
                "SELECT 1 as alive",
                fetch_one=True
            )
            
            db_status = "ok" if row and row[0] == 1 else "error"
            
            return Response({
                "status": "healthy",
                "database": db_status,
                "service": "SmartSales Backend"
            })
        except Exception as e:
            return Response({
                "status": "unhealthy",
                "database": "error",
                "error": str(e),
                "service": "SmartSales Backend"
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
