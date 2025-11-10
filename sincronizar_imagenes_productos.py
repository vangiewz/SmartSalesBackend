import os
import psycopg2
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Cargar variables desde .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # service_role
NEON_DSN = os.getenv("DATABASE_URL")

BUCKET = "productos"
# Estructura dentro del bucket:
# productos (bucket) / productos (carpeta) / 99907460-... (carpeta) / 8.png, 9.png, 10.jpg...
FOLDER = "productos/99907460-c180-4c1b-ad73-139ab638751c"

def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY en el .env")

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Conectado a Supabase")

    # Listar archivos dentro de esa carpeta
    files = supabase.storage.from_(BUCKET).list(path=FOLDER)
    print(f"🔍 {len(files)} archivos encontrados en '{BUCKET}/{FOLDER}'")

    conn = psycopg2.connect(NEON_DSN)
    cur = conn.cursor()

    actualizados = 0
    sin_match = []

    for f in files:
        filename = f["name"]              # ej: "10.jpg"
        name_no_ext = Path(filename).stem # "10"

        # id del producto = número del archivo
        try:
            product_id = int(name_no_ext)
        except ValueError:
            sin_match.append(filename)
            continue

        # Path completo RELATIVO dentro del bucket
        # Ej: "productos/9990.../10.jpg"
        object_path = f"{FOLDER}/{filename}"

        # Lo que guardamos en imagen_key es SOLO el path, no la URL completa
        imagen_key = object_path

        # Actualizar imagen_key (si querés solo los vacíos, agrega la condición IS NULL)
        cur.execute(
            """
            UPDATE producto
            SET imagen_key = %s
            WHERE id = %s
            """,
            (imagen_key, product_id),
        )

        if cur.rowcount > 0:
            actualizados += 1
        else:
            sin_match.append(filename)

    conn.commit()
    cur.close()
    conn.close()

    print(f"✅ Productos actualizados: {actualizados}")
    if sin_match:
        print("⚠️ Archivos sin match en DB:")
        for n in sin_match:
            print("   -", n)

if __name__ == "__main__":
    main()
