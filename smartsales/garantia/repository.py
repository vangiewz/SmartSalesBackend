# smartsales/garantia/repository.py
from typing import Any, List, Optional, Tuple
from smartsales.db_utils import execute_query_with_retry

def get_venta_usuario_id(venta_id: int) -> Optional[str]:
    row = execute_query_with_retry(
        "SELECT usuario_id FROM venta WHERE id=%s",
        [venta_id],
        fetch_one=True
    )
    return row[0] if row else None

def get_detalleventa(venta_id: int, producto_id: int) -> Optional[Tuple[int, Any]]:
    # (cantidad_comprada, limitegarantia)
    row = execute_query_with_retry(
        "SELECT cantidad, limitegarantia FROM detalleventa WHERE venta_id=%s AND producto_id=%s",
        [venta_id, producto_id],
        fetch_one=True
    )
    return (int(row[0]), row[1]) if row else None

def get_producto_info(producto_id: int) -> Optional[Tuple[int, str, str]]:
    # (stock, nombre, imagen_key)
    row = execute_query_with_retry(
        "SELECT stock, nombre, COALESCE(imagen_key,'') FROM producto WHERE id=%s",
        [producto_id],
        fetch_one=True
    )
    return (int(row[0]), row[1], row[2]) if row else None

def get_producto_stock(producto_id: int) -> Optional[int]:
    row = execute_query_with_retry(
        "SELECT stock FROM producto WHERE id=%s",
        [producto_id],
        fetch_one=True
    )
    return int(row[0]) if row else None

def get_producto_vendedor_id(producto_id: int) -> Optional[str]:
    """Obtiene el id_vendedor de un producto"""
    row = execute_query_with_retry(
        "SELECT id_vendedor FROM producto WHERE id=%s",
        [producto_id],
        fetch_one=True
    )
    return str(row[0]) if row else None

def descontar_stock(producto_id: int, cantidad: int) -> None:
    execute_query_with_retry(
        "UPDATE producto SET stock = stock - %s WHERE id=%s",
        [cantidad, producto_id]
    )

def insert_garantia(venta_id: int, producto_id: int, cantidad: int, motivo: str) -> int:
    row = execute_query_with_retry(
        """
        INSERT INTO garantia (venta_id, producto_id, cantidad, motivo)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        [venta_id, producto_id, cantidad, motivo],
        fetch_one=True
    )
    return int(row[0])

def get_garantia(venta_id: int, producto_id: int, garantia_id: int):
    return execute_query_with_retry(
        """
        SELECT g.id, g.estadogarantia_id, eg.nombre, g.cantidad, g.motivo, g.hora, g.reemplazo
        FROM garantia g
        JOIN estadogarantia eg ON eg.id = g.estadogarantia_id
        WHERE g.venta_id=%s AND g.producto_id=%s AND g.id=%s
        """,
        [venta_id, producto_id, garantia_id],
        fetch_one=True
    )

def get_garantia_simple(garantia_id: int) -> Optional[Tuple[int, int]]:
    """Obtiene venta_id y producto_id de una garantía"""
    row = execute_query_with_retry(
        "SELECT venta_id, producto_id FROM garantia WHERE id=%s",
        [garantia_id],
        fetch_one=True
    )
    return (int(row[0]), int(row[1])) if row else None

def get_garantia_detalle(venta_id: int, producto_id: int, garantia_id: int):
    """Obtiene detalle completo de una garantía incluyendo datos del cliente y técnico"""
    return execute_query_with_retry(
        """
        SELECT 
            g.id AS garantia_id,
            g.venta_id,
            g.producto_id,
            p.nombre AS producto_nombre,
            COALESCE(p.imagen_key, '') AS imagen_key,
            '' AS producto_descripcion,
            p.tiempogarantia AS producto_garantia_dias,
            v.hora AS fecha_venta,
            g.hora AS fecha_solicitud,
            dv.limitegarantia AS limite_garantia,
            eg.nombre AS estado,
            g.motivo,
            g.cantidad,
            CASE 
                WHEN g.reemplazo = true THEN 'Reemplazar'
                WHEN g.reemplazo = false THEN 'Reparar'
                ELSE NULL
            END AS evaluacion,
            '' AS comentario_tecnico,
            g.hora AS fecha_evaluacion,
            NULL AS tecnico_id,
            '' AS tecnico_nombre,
            g.reemplazo AS es_reemplazo,
            COALESCE(u.nombre, '') AS cliente_nombre,
            u.correo AS cliente_email,
            COALESCE(u.telefono, '') AS cliente_telefono
        FROM garantia g
        JOIN estadogarantia eg ON eg.id = g.estadogarantia_id
        JOIN venta v ON v.id = g.venta_id
        JOIN usuario u ON u.id = v.usuario_id
        JOIN detalleventa dv ON dv.venta_id = g.venta_id AND dv.producto_id = g.producto_id
        JOIN producto p ON p.id = g.producto_id
        WHERE g.venta_id=%s AND g.producto_id=%s AND g.id=%s
        """,
        [venta_id, producto_id, garantia_id],
        fetch_one=True
    )


def set_garantia_estado(venta_id: int, producto_id: int, garantia_id: int, estado_nombre: str, reemplazo: Optional[bool]) -> None:
    row = execute_query_with_retry(
        "SELECT id FROM estadogarantia WHERE nombre=%s LIMIT 1",
        [estado_nombre],
        fetch_one=True
    )
    estado_id = int(row[0])
    execute_query_with_retry(
        """
        UPDATE garantia
        SET estadogarantia_id=%s, reemplazo=%s
        WHERE venta_id=%s AND producto_id=%s AND id=%s
        """,
        [estado_id, reemplazo, venta_id, producto_id, garantia_id]
    )

def list_garantias(
    scope_user_id: Optional[str],
    estado: Optional[str],
    venta_id: Optional[int],
    producto_id: Optional[int],
    desde: Optional[str],
    hasta: Optional[str],
    q: Optional[str],
    cliente: Optional[str],
    page: int,
    page_size: int
) -> Tuple[int, List[Tuple]]:
    filters, params = [], []

    if scope_user_id:
        filters.append("v.usuario_id = %s")
        params.append(scope_user_id)
    if estado:
        filters.append("eg.nombre = %s")
        params.append(estado)
    if venta_id:
        filters.append("g.venta_id = %s")
        params.append(venta_id)
    if producto_id:
        filters.append("g.producto_id = %s")
        params.append(producto_id)
    if desde:
        filters.append("g.hora >= %s")
        params.append(desde)
    if hasta:
        filters.append("g.hora <= %s")
        params.append(hasta)
    if q:
        filters.append("LOWER(p.nombre) LIKE LOWER(%s)")
        params.append(f"%{q}%")
    if cliente and not scope_user_id:
        filters.append("LOWER(u.correo) LIKE LOWER(%s)")
        params.append(f"%{cliente}%")

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    count_row = execute_query_with_retry(
        f"""
        SELECT COUNT(*)
        FROM garantia g
        JOIN venta v         ON v.id = g.venta_id
        JOIN producto p      ON p.id = g.producto_id
        JOIN usuario u       ON u.id = v.usuario_id
        JOIN estadogarantia eg ON eg.id = g.estadogarantia_id
        {where}
        """,
        params, fetch_one=True
    )
    total = int(count_row[0]) if count_row else 0

    offset = (page - 1) * page_size
    rows = execute_query_with_retry(
        f"""
        SELECT
          g.venta_id, g.producto_id, g.id AS garantia_id,
          eg.nombre AS estado, g.cantidad, g.motivo, g.hora, g.reemplazo,
          p.nombre AS producto_nombre, COALESCE(p.imagen_key,'') AS imagen_key,
          dv.limitegarantia
        FROM garantia g
        JOIN venta v         ON v.id = g.venta_id
        JOIN producto p      ON p.id = g.producto_id
        JOIN detalleventa dv ON dv.venta_id = g.venta_id AND dv.producto_id = g.producto_id
        JOIN estadogarantia eg ON eg.id = g.estadogarantia_id
        JOIN usuario u       ON u.id = v.usuario_id
        {where}
        ORDER BY g.hora DESC
        LIMIT %s OFFSET %s
        """,
        params + [page_size, offset],
        fetch_all=True
    )
    return total, rows
