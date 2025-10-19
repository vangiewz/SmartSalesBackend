# smartsales/authsupabase/api.py
import os
import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

AUTH_URL = f"{SUPABASE_URL}/auth/v1"

class SupabaseError(Exception):
    pass

def create_user_admin(email: str, password: str, user_metadata: dict | None = None) -> dict:
    """
    Crea un usuario con la Admin API (requiere SERVICE ROLE KEY).
    Retorna el JSON con el 'id' (UUID).
    """
    url = f"{AUTH_URL}/admin/users"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "email": email,
        "password": password,
        "email_confirm": True,  # marcar email como verificado (opcional)
        "user_metadata": user_metadata or {},
    }
    r = requests.post(url, headers=headers, json=payload, timeout=20)
    if r.status_code >= 400:
        raise SupabaseError(f"create_user_admin error {r.status_code}: {r.text}")
    return r.json()

def sign_in_password(email: str, password: str) -> dict:
    """
    Inicia sesión con email/password y devuelve tokens + user.
    """
    url = f"{AUTH_URL}/token?grant_type=password"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
    }
    payload = {"email": email, "password": password}
    r = requests.post(url, headers=headers, json=payload, timeout=20)
    if r.status_code >= 400:
        raise SupabaseError(f"sign_in_password error {r.status_code}: {r.text}")
    return r.json()
