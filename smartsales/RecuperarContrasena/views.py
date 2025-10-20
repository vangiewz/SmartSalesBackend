from urllib.parse import urlparse
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .serializers import PasswordResetRequestSerializer, PasswordResetConfirmSerializer
from .services import send_recovery_email, update_password_with_token, PasswordResetError

def _build_front_reset_url(request) -> str | None:
    """
    Construye http(s)://host[:port]/reset-password a partir de Origin/Referer.
    Si no hay headers válidos, retorna None → Supabase usará Site URL.
    """
    origin = request.headers.get("Origin") or request.headers.get("Referer")
    if not origin:
        return None
    u = urlparse(origin)
    if not u.scheme or not u.netloc:
        return None
    return f"{u.scheme}://{u.netloc}/reset-password"

class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        s = PasswordResetRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        email = s.validated_data["email"].strip().lower()
        redirect_to = _build_front_reset_url(request)

        try:
            send_recovery_email(email, redirect_to)
        except PasswordResetError:
            pass  # No revelamos si el email existe

        return Response({"message": "Si el correo existe, recibirás un enlace de recuperación"}, status=200)

class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        s = PasswordResetConfirmSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        token = s.validated_data["token"].strip()
        new_password = s.validated_data["new_password"]

        try:
            update_password_with_token(token, new_password)
            return Response({"message": "Contraseña actualizada correctamente"}, status=200)
        except PasswordResetError as e:
            return Response({"detail": str(e)}, status=400)
