# smartsales/carrito_voz/repository.py

from typing import List, Dict, Optional
from django.db import connection


def _ejecutar_busqueda(sql: str, params: list) -> List[Dict]:
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()

    resultados: List[Dict] = []
    for row in rows:
        resultados.append(
            {
                "id": row[0],
                "nombre": row[1],
                "precio": row[2],
            }
        )
    return resultados


def _singularizar_fragmento(fragmento: str) -> Optional[str]:
    """
    Intenta pasar TODAS las palabras del fragmento a singular
    con reglas simples:
      - palabras largas que terminan en 'es' -> sin 'es'
      - palabras que terminan en 's' -> sin 's'

    Ejemplos:
      'refrigeradores samsung' -> 'refrigerador samsung'
      'lavadoras samsung'      -> 'lavadora samsung'
    """
    texto = fragmento.strip().lower()
    if not texto:
        return None

    palabras = texto.split()
    nuevas: List[str] = []
    cambiadas = False

    for p in palabras:
        base = p
        # Evitamos tocar palabras muy cortas tipo 'lg', 'tv', etc.
        if len(p) > 5 and p.endswith("es"):
            base = p[:-2]          # refrigeradores -> refrigerador
        elif len(p) > 4 and p.endswith("s"):
            base = p[:-1]          # lavadoras -> lavadora, cocinas -> cocina

        if base != p:
            cambiadas = True
        nuevas.append(base)

    if not cambiadas:
        return None

    return " ".join(nuevas)


def buscar_producto_por_fragmento(
    fragmento: str,
    limite: int = 3,
    id_vendedor: Optional[str] = None,
) -> List[Dict]:
    """
    Busca productos cuyo nombre contenga el fragmento (ILIKE).

    - Si se pasa id_vendedor:
        1) Intenta buscar solo productos de ese vendedor.
        2) Si no encuentra ninguno, hace fallback a búsqueda global.
    - Si no se pasa id_vendedor: búsqueda global directa.

    Si no hay resultados, intenta de nuevo usando una versión
    "singular" del fragmento (refrigeradores -> refrigerador,
    lavadoras -> lavadora, etc.).
    """
    fragmento = fragmento.strip().lower()
    if not fragmento:
        return []

    base_sql = """
        SELECT id, nombre, precio
        FROM producto
        WHERE LOWER(nombre) LIKE %s
    """

    def _buscar(fragmento_busqueda: str) -> List[Dict]:
        # 1) Intento con filtro por vendedor
        if id_vendedor:
            sql_vendedor = base_sql + " AND id_vendedor = %s ORDER BY nombre LIMIT %s"
            params_vendedor = [f"%{fragmento_busqueda}%", str(id_vendedor), limite]
            resultados_vendedor = _ejecutar_busqueda(sql_vendedor, params_vendedor)
            if resultados_vendedor:
                return resultados_vendedor

        # 2) Fallback: búsqueda global (sin vendedor)
        sql_global = base_sql + " ORDER BY nombre LIMIT %s"
        params_global = [f"%{fragmento_busqueda}%", limite]
        resultados_global = _ejecutar_busqueda(sql_global, params_global)
        return resultados_global

    # Primero probamos con el fragmento tal cual
    resultados = _buscar(fragmento)
    if resultados:
        return resultados

    # Si no hubo resultados, probamos con versión "singular"
    frag_singular = _singularizar_fragmento(fragmento)
    if frag_singular and frag_singular != fragmento:
        resultados_singular = _buscar(frag_singular)
        if resultados_singular:
            return resultados_singular

    return []
