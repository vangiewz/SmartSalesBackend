import uuid, os, requests
from urllib.parse import quote
from smartsales.authsupabase.api import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

# Usamos el bucket público ya creado en tu proyecto:
BUCKET = "productos"

def _safe_key(user_id: str, original_name: str) -> str:
    base = os.path.basename(original_name).replace(" ", "_")
    return f"productos/{user_id}/{uuid.uuid4().hex}_{base}"

def upload_image(file_bytes: bytes, filename: str, user_id: str) -> str:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("SUPABASE_URL o SERVICE_ROLE_KEY no configurados.")
    key = _safe_key(user_id, filename)
    url = f"{SUPABASE_URL}/storage/v1/object/{quote(BUCKET)}/{quote(key)}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/octet-stream",
    }
    resp = requests.post(url, headers=headers, data=file_bytes)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Error subiendo imagen: {resp.status_code} {resp.text}")
    return key

def delete_image_if_exists(imagen_key: str) -> None:
    if not imagen_key:
        return
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("SUPABASE_URL o SERVICE_ROLE_KEY no configurados.")
    url = f"{SUPABASE_URL}/storage/v1/object/{quote(BUCKET)}/{quote(imagen_key)}"
    headers = {"Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}"}
    requests.delete(url, headers=headers)  # si no existe, ignoramos

def public_url(imagen_key: str) -> str:
    if not imagen_key:
        return None
    return f"{SUPABASE_URL}/storage/v1/object/public/{quote(BUCKET)}/{quote(imagen_key)}"
