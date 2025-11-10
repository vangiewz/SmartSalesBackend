import os

# 📁 Ruta de tu carpeta local
carpeta = r"C:\Users\Leonardo\Downloads\imagenes\lavadora"

# 🔢 Número inicial (por ejemplo, 8)
inicio = 118

# 🔍 Listar todos los archivos de la carpeta (ignorando carpetas)
archivos = sorted([f for f in os.listdir(carpeta) if os.path.isfile(os.path.join(carpeta, f))])

for i, archivo in enumerate(archivos, start=inicio):
    # Extraer la extensión (.jpg, .png, etc.)
    _, extension = os.path.splitext(archivo)

    # Nuevo nombre con numeración secuencial
    nuevo_nombre = f"{i}{extension}"

    ruta_vieja = os.path.join(carpeta, archivo)
    ruta_nueva = os.path.join(carpeta, nuevo_nombre)

    os.rename(ruta_vieja, ruta_nueva)
    print(f"✅ {archivo} → {nuevo_nombre}")

print("🎉 Renombrado completado correctamente.")
