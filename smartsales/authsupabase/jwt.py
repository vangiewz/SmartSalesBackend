# smartsales/authsupabase/jwt.py
import os
import jwt
from jwt import InvalidTokenError
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions

SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")

class SimpleUser:
    def __init__(self, user_id: str, email: str | None):
        self.id = user_id
        self.email = email or ""
        self.is_authenticated = True

class SupabaseJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        token = auth.split(" ", 1)[1].strip()
        if not token:
            return None

        if not SUPABASE_JWT_SECRET:
            raise exceptions.AuthenticationFailed("SUPABASE_JWT_SECRET no configurado.")

        try:
            # ⬇️ Desactivar verificación de audience para tokens de Supabase
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False},   # ← ESTA LÍNEA
            )
        except InvalidTokenError as e:
            raise exceptions.AuthenticationFailed(f"Token inválido: {e}")

        user_id = payload.get("sub") or payload.get("user_id") or ""
        email = payload.get("email")
        if not user_id:
            raise exceptions.AuthenticationFailed("Token sin 'sub' (user id).")

        return (SimpleUser(user_id=user_id, email=email), None)
