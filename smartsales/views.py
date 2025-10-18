from django.db import transaction, connection
from django.contrib.auth.models import User
from django.contrib.auth import authenticate

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Usuario, Rol
from .serializers import (
    UsuarioMeSerializer,
    RegisterSerializer,
    LoginSerializer,
)

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        email = (request.user.email or "").strip().lower()
        if not email:
            return Response({"detail": "El usuario autenticado no tiene email."}, status=400)

        try:
            u = Usuario.objects.get(correo__iexact=email)
        except Usuario.DoesNotExist:
            return Response({"detail": "No existe 'usuario' con ese email en la BD."}, status=404)

        # roles por join desde tus tablas
        from .models import Rol  # import local para evitar import circular
        roles_qs = Rol.objects.filter(rolesusuario__usuario=u).distinct().values_list("nombre", flat=True)

        data = UsuarioMeSerializer(u).data
        data["roles"] = list(roles_qs)
        return Response(data)

class RegisterView(APIView):
    """
    Registro SOLO con email + password (+ nombre/telefono):
    - Crea auth_user con username=email
    - Inserta en 'usuario'
    - Inserta rol 'Cliente' en 'rolesusuario' (SQL crudo por PK compuesta)
    - Devuelve tokens + perfil
    """
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        s = RegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data

        email = data["email"].strip().lower()
        password = data["password"]
        nombre = data["nombre"].strip()
        telefono = data.get("telefono", "").strip() or None

        # 1) Usuario Django (auth) -> username=email
        dj_user = User.objects.create_user(username=email, email=email, password=password)

        # 2) Fila en tu tabla 'usuario' (Supabase)
        u = Usuario.objects.create(nombre=nombre, telefono=telefono, correo=email)

        # 3) Rol por defecto: 'Cliente' (o id=1)
        rol = Rol.objects.filter(nombre__iexact="Cliente").first() or Rol.objects.filter(id=1).first()
        if not rol:
            return Response({"detail": "No existe rol 'Cliente' (ni id=1) en la tabla roles."}, status=500)

        # 3b) Insertar en rolesusuario con SQL crudo (PK compuesta)
        with connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO rolesusuario (usuario_id, rol_id)
                VALUES (%s, %s)
                ON CONFLICT (usuario_id, rol_id) DO NOTHING
                """,
                [u.id, rol.id],
            )

        # 4) Tokens JWT
        refresh = RefreshToken.for_user(dj_user)
        return Response({
            "user": {
                "email": dj_user.email,
                "nombre": u.nombre,
                "telefono": u.telefono,
                "roles": [rol.nombre],
            },
            "tokens": {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
        }, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    """
    Login SOLO con email + password:
    - authenticate(username=email, password=...)
    - Devuelve tokens y perfil (usuario + roles desde Supabase)
    """
    permission_classes = [AllowAny]

    def post(self, request):
        ser = LoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        email = ser.validated_data["email"].strip().lower()
        pw = ser.validated_data["password"]

        # authenticate siempre usa 'username', por eso pasamos username=email
        user = authenticate(request, username=email, password=pw)
        if user is None:
            return Response({"detail": "Credenciales inválidas."}, status=401)

        # Tokens
        refresh = RefreshToken.for_user(user)

        # Perfil + roles desde tus tablas (mapear por email)
        perfil = {"email": user.email, "nombre": None, "telefono": None, "roles": []}
        try:
            u = Usuario.objects.get(correo__iexact=user.email)
            from .models import Rol  # import local para evitar import circular
            roles_qs = Rol.objects.filter(rolesusuario__usuario=u).distinct().values_list("nombre", flat=True)
            perfil.update({"nombre": u.nombre, "telefono": u.telefono, "roles": list(roles_qs)})
        except Usuario.DoesNotExist:
            pass

        return Response({
            "user": perfil,
            "tokens": {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
        })
