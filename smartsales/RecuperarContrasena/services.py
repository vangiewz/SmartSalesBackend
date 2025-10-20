import os
import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
AUTH_URL = f"{SUPABASE_URL}/auth/v1"

class PasswordResetError(Exception):
    pass

def _ensure_config():
    if not SUPABASE_URL:
        raise PasswordResetError("SUPABASE_URL no está configurado.")
    if not SUPABASE_ANON_KEY:
        raise PasswordResetError("SUPABASE_ANON_KEY no está configurado.")

def send_recovery_email(email: str, redirect_to: str | None) -> dict:
    _ensure_config()
    url = f"{AUTH_URL}/recover"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"email": email}
    if redirect_to:
        payload["redirect_to"] = redirect_to  # p.ej. http://localhost:5173/reset-password

    r = requests.post(url, json=payload, headers=headers, timeout=15)
    if r.status_code in (200, 204):
        return r.json() if r.text else {}
    raise PasswordResetError(f"Error Supabase recover: {r.status_code} {r.text}")

def update_password_with_token(recovery_token: str, new_password: str) -> dict:
    _ensure_config()
    url = f"{AUTH_URL}/user"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {recovery_token}",
        "Content-Type": "application/json",
    }
    r = requests.put(url, json={"password": new_password}, headers=headers, timeout=15)
    if r.status_code in (200, 201):
        return r.json()
    if r.status_code == 401:
        raise PasswordResetError("Token inválido o expirado")
    if r.status_code == 422:
        raise PasswordResetError("La contraseña no cumple los requisitos")
    raise PasswordResetError(f"Error al actualizar contraseña: {r.status_code} {r.text}")
