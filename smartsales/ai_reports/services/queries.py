from textwrap import dedent
from typing import List

BASE_JOINS = dedent("""
    FROM   detalleventa d
    JOIN   venta v         ON v.id = d.venta_id
    JOIN   producto p      ON p.id = d.producto_id
    LEFT JOIN marca m      ON m.id = p.marca_id
    LEFT JOIN tipoproducto t ON t.id = p.tipoproducto_id
    LEFT JOIN usuario u    ON u.id = v.usuario_id
""")

SELECTS = {
    'ventas_por_mes':       "SELECT date_trunc('month', v.hora) AS mes, SUM(v.total) AS monto",
    'ventas_por_marca':     "SELECT COALESCE(m.nombre,'(Sin marca)') AS marca, SUM(d.cantidad*p.precio) AS monto, SUM(d.cantidad) AS unidades",
    'ventas_por_categoria': "SELECT COALESCE(t.nombre,'(Sin categoría)') AS categoria, SUM(d.cantidad*p.precio) AS monto, SUM(d.cantidad) AS unidades",
    'top_productos':        "SELECT p.nombre AS producto, SUM(d.cantidad) AS unidades, SUM(d.cantidad*p.precio) AS monto",
    'ventas_por_cliente':   "SELECT u.nombre AS cliente, COUNT(DISTINCT v.id) AS n_ventas, SUM(v.total) AS monto",
    'ticket_promedio':      "SELECT AVG(v.total) AS ticket_promedio, COUNT(*) AS n_ventas",

    # Detalle por defecto
    'ventas_detalladas': dedent("""
        SELECT
            v.id                          AS venta_id,
            v.hora                        AS fecha,
            COALESCE(u.nombre,'(Sin cliente)')      AS cliente,
            COALESCE(v.direccion,'')               AS direccion,
            p.id                          AS producto_id,
            p.nombre                      AS producto,
            COALESCE(m.nombre,'(Sin marca)')       AS marca,
            COALESCE(t.nombre,'(Sin categoría)')   AS categoria,
            d.cantidad                    AS cantidad,
            p.precio                      AS precio_unit,
            (d.cantidad * p.precio)       AS subtotal,
            v.total                       AS total_venta,
            d.limitegarantia              AS limitegarantia
    """),

    'garantias_por_estado': "SELECT e.nombre AS estado, COUNT(*) AS n_casos FROM garantia g JOIN estadogarantia e ON e.id=g.estadogarantia_id",
}

GROUPS = {
    'ventas_por_mes':       "GROUP BY 1 ORDER BY 1",
    'ventas_por_marca':     "GROUP BY categoria ORDER BY monto DESC",
    'ventas_por_categoria': "GROUP BY categoria ORDER BY monto DESC",
    'top_productos':        "GROUP BY p.nombre ORDER BY unidades DESC LIMIT 10",
    'ventas_por_cliente':   "GROUP BY u.nombre ORDER BY monto DESC",
    'ticket_promedio':      "",
    'garantias_por_estado': "GROUP BY e.nombre ORDER BY n_casos DESC",
}

# ---------- normalización y alias ----------
def _strip_accents(s: str) -> str:
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', s or '') if unicodedata.category(c) != 'Mn')

def _norm(s: str) -> str:
    return _strip_accents(s).lower().strip()

# Aliases de DETALLE
DETALLADAS_COLUMNS = {
    'venta_id':       "v.id AS venta_id",
    'fecha':          "v.hora AS fecha",
    'cliente':        "COALESCE(u.nombre,'(Sin cliente)') AS cliente",
    'direccion':      "COALESCE(v.direccion,'') AS direccion",
    'producto_id':    "p.id AS producto_id",
    'producto':       "p.nombre AS producto",
    'marca':          "COALESCE(m.nombre,'(Sin marca)') AS marca",
    'categoria':      "COALESCE(t.nombre,'(Sin categoría)') AS categoria",
    'cantidad':       "d.cantidad AS cantidad",
    'precio_unit':    "p.precio AS precio_unit",
    'subtotal':       "(d.cantidad * p.precio) AS subtotal",
    'total_venta':    "v.total AS total_venta",
    'limitegarantia': "d.limitegarantia AS limitegarantia",
}

DETALLADAS_SYNONYMS = {
    'venta_id':       ['venta id', 'id venta', 'nro venta', 'numero venta', 'order id', 'id'],
    'fecha':          ['fecha', 'fecha venta', 'fecha compra', 'dia', 'día'],
    'cliente':        ['cliente', 'nombre cliente', 'razon social', 'nombre', 'customer'],
    'direccion':      ['direccion', 'dirección', 'domicilio', 'address'],
    'producto_id':    ['producto id', 'id producto', 'sku id', 'product id'],
    'producto':       ['producto', 'nombre producto', 'item', 'articulo', 'artículo', 'sku', 'product'],
    'marca':          ['marca', 'brand'],
    'categoria':      ['categoria', 'categoría', 'category', 'tipo'],
    'cantidad':       ['cantidad', 'qty', 'quantity', 'count', 'conteo', 'unidades', 'unidades vendidas'],
    'precio_unit':    ['precio unitario', 'unit price', 'precio promedio', 'precio'],
    'subtotal':       ['subtotal', 'importe parcial', 'monto parcial'],
    'total_venta':    ['total venta', 'monto total', 'total', 'total pagado', 'importe total'],
    'limitegarantia': ['limite garantia', 'límite garantía', 'garantia', 'garantía', 'fecha garantia'],
}

# Clave de agrupación
GROUP_BY_KEY_SQL = {
    'producto':  "p.nombre AS producto",
    'marca':     "COALESCE(m.nombre,'(Sin marca)') AS marca",
    'categoria': "COALESCE(t.nombre,'(Sin categoría)') AS categoria",
    'cliente':   "COALESCE(u.nombre,'(Sin cliente)') AS cliente",
    'mes':       "date_trunc('month', v.hora) AS mes",
}

def _canon_group_key(k: str | None) -> str | None:
    if not k: return None
    k = _norm(k)
    if k.startswith('categor'): return 'categoria'
    if k in GROUP_BY_KEY_SQL: return k
    if k in ('brand',): return 'marca'
    if k in ('product', 'item', 'articulo', 'artículo', 'sku'): return 'producto'
    if k in ('customer', 'usuario'): return 'cliente'
    if k in ('month', 'meses'): return 'mes'
    return None

def _infer_group_key_from_requested(requested: List[str]) -> str | None:
    s = set(requested or [])
    has_agg = any(t in s for t in ('n_compras', 'monto_total', 'monto', 'total', 'total_venta'))
    if not has_agg:
        return None
    for key in ('cliente', 'producto', 'marca', 'categoria', 'mes'):
        if key in s:
            return 'categoria' if key == 'categoria' else key
    return None

# Agregados canónicos y sinónimos
GROUP_AGG_CANON_SYNS = {
    'n_compras':   ['n compras', 'numero compras', 'número compras', 'cantidad compras', 'compras realizadas', 'orders', 'ordenes'],
    'monto_total': ['monto total', 'total', 'total pagado', 'importe total', 'monto'],
    'cantidad':    ['cantidad', 'unidades', 'qty', 'quantity'],
    'precio_unit': ['precio unitario', 'unit price', 'precio promedio', 'precio'],
    'fecha':       ['fecha', 'fechas', 'rango fechas', 'rango_fechas', 'periodo', 'período', 'rango de fechas'],
    'fecha_min':   ['fecha inicio', 'desde', 'min fecha', 'fecha minima', 'fecha mínima', 'fecha desde', 'inicio'],
    'fecha_max':   ['fecha fin', 'hasta', 'max fecha', 'fecha maxima', 'fecha máxima', 'fecha hasta', 'fin'],
}

def _to_detalle_aliases(requested: List[str]) -> List[str]:
    if not requested: return []
    out: List[str] = []
    for req in requested:
        r = _norm(req)
        best = None
        for alias in DETALLADAS_COLUMNS.keys():
            if _norm(alias) == r:
                best = alias; break
        if not best:
            for alias, syns in DETALLADAS_SYNONYMS.items():
                if r == _norm(alias) or any(r == _norm(s) for s in syns) or r in _norm(alias) or any(_norm(s) in r for s in syns):
                    best = alias; break
        if best and best not in out:
            out.append(best)
    return out

def _to_group_aggs(requested: List[str]) -> List[str]:
    if not requested: return []
    out: List[str] = []
    for req in requested:
        r = _norm(req)
        if r in ('rango_fechas', 'rango fechas'):  # se maneja como 'fecha'
            r = 'fecha'
        canon = None
        if r in GROUP_AGG_CANON_SYNS:
            canon = r
        else:
            for k, syns in GROUP_AGG_CANON_SYNS.items():
                if r == k or any(r == _norm(s) for s in syns) or r in k or any(_norm(s) in r or r in _norm(s) for s in syns):
                    canon = k; break
        if canon and canon not in out:
            out.append(canon)
    return out

def _build_group_aggs_sql(group_key: str, aggs: List[str]) -> List[str]:
    parts: List[str] = []
    for a in aggs:
        if a == 'n_compras':
            parts.append("COUNT(DISTINCT v.id) AS n_compras")
        elif a == 'monto_total':
            if group_key == 'cliente':
                parts.append("SUM(v.total) AS monto_total")
            else:
                parts.append("SUM(d.cantidad * p.precio) AS monto_total")
        elif a == 'cantidad':
            parts.append("SUM(d.cantidad) AS cantidad")
        elif a == 'precio_unit':
            parts.append("AVG(p.precio) AS precio_unit")
        elif a == 'fecha':
            parts.append("MIN(v.hora) AS fecha_min")
            parts.append("MAX(v.hora) AS fecha_max")
        elif a == 'fecha_min':
            parts.append("MIN(v.hora) AS fecha_min")
        elif a == 'fecha_max':
            parts.append("MAX(v.hora) AS fecha_max")
        # otros alias se podrían agregar aquí
    return parts

def _build_select_detalle(aliases: List[str]) -> str:
    if not aliases: return ""
    parts = [DETALLADAS_COLUMNS[a] for a in aliases if a in DETALLADAS_COLUMNS]
    if not parts: return ""
    return "SELECT " + ",\n            ".join(parts)

def build_sql(intent: str, filters: dict):
    """
    Devuelve (sql, params) con WHERE y SELECT dinámico.
    - Siempre filtra por fechas.
    - Filtros opcionales: producto, marca, categoria, cliente, direccion.
    - ventas_detalladas:
        a) si hay _group_by (o se infiere) → SELECT agregado dinámico con columnas pedidas (incluye n_compras, monto_total, fechas)
        b) si hay _columns sin _group_by → SELECT de detalle recortado
        c) si no hay ninguno → SELECT completo
    """
    where = []
    params = []

    date_col = 'v.hora' if intent not in ('garantias_por_estado',) else 'g.hora'
    where.append(f"{date_col} >= %s AND {date_col} < %s")

    has_item_filter = False
    if filters:
        if prod := filters.get('producto'):
            where.append("p.nombre ILIKE %s")
            params.append(f"%{prod}%")
            has_item_filter = True
        if marca := filters.get('marca'):
            where.append("m.nombre ILIKE %s")
            params.append(f"%{marca}%")
            has_item_filter = True
        if cat := filters.get('categoria'):
            where.append("t.nombre ILIKE %s")
            params.append(f"%{cat}%")
            has_item_filter = True
        if cli := filters.get('cliente'):
            where.append("u.nombre ILIKE %s")
            params.append(f"%{cli}%")
        if dire := filters.get('direccion'):
            where.append("v.direccion ILIKE %s")
            params.append(f"%{dire}%")

    where_sql = "WHERE " + " AND ".join(where) if where else ""

    # ----- Garantías -----
    if intent == 'garantias_por_estado':
        sql = f"""
            {SELECTS[intent]}
            JOIN detalleventa d ON d.venta_id = g.venta_id AND d.producto_id = g.producto_id
            JOIN venta v ON v.id = g.venta_id
            JOIN producto p ON p.id = d.producto_id
            LEFT JOIN marca m ON m.id = p.marca_id
            LEFT JOIN tipoproducto t ON t.id = p.tipoproducto_id
            LEFT JOIN usuario u ON u.id = v.usuario_id
            {where_sql}
            {GROUPS[intent]};
        """
        return dedent(sql), params

    # ----- Ventas por mes -----
    if intent == 'ventas_por_mes':
        select = (
            "SELECT date_trunc('month', v.hora) AS mes, SUM(d.cantidad * p.precio) AS monto"
            if has_item_filter else
            "SELECT date_trunc('month', v.hora) AS mes, SUM(v.total) AS monto"
        )
        sql = f"""
            {select}
            {BASE_JOINS}
            {where_sql}
            GROUP BY 1
            ORDER BY 1;
        """
        return dedent(sql), params

    # ----- Ventas detalladas (dinámico) -----
    if intent == 'ventas_detalladas':
        requested_cols: List[str] = []
        group_key = None
        if isinstance(filters, dict):
            requested_cols = filters.get('_columns') or []
            requested_cols = [_norm(x) for x in requested_cols if isinstance(x, str) and x.strip()]
            group_key = _canon_group_key(filters.get('_group_by')) or _infer_group_key_from_requested(requested_cols)

        # a) AGRUPADO
        if group_key:
            key_sql = GROUP_BY_KEY_SQL.get(group_key, GROUP_BY_KEY_SQL['producto'])
            aggs = _to_group_aggs(requested_cols)
            if not aggs:
                aggs = ['n_compras', 'monto_total']
            aggs = [a for a in aggs if a not in (group_key,)]
            agg_parts = _build_group_aggs_sql(group_key, aggs)
            select_sql = "SELECT " + ",\n            ".join([key_sql] + agg_parts)

            group_by_sql = "GROUP BY 1"

            # ORDER BY preferente
            order_by = None
            for cand in ('monto_total', 'n_compras', 'cantidad'):
                if cand in aggs:
                    order_by = cand; break
            if order_by:
                order_by_sql = f"ORDER BY {order_by} DESC"
            else:
                alias_key = 'categoria' if group_key == 'categoria' else group_key
                order_by_sql = f"ORDER BY {alias_key}"

            sql = f"""
                {select_sql}
                {BASE_JOINS}
                {where_sql}
                {group_by_sql}
                {order_by_sql};
            """
            return dedent(sql), params

        # b) DETALLE recortado
        if requested_cols:
            requested_cols = [c for c in requested_cols if c not in ('rango_fechas',)]
            aliases = _to_detalle_aliases(requested_cols)
            select = _build_select_detalle(aliases) if aliases else ""
            if not select:
                select = SELECTS[intent].strip()
            order_parts: List[str] = []
            order_parts.append('fecha' if 'fecha' in aliases else 'v.hora')
            order_parts.append('venta_id' if 'venta_id' in aliases else 'v.id')
            order_parts.append('producto' if 'producto' in aliases else 'p.nombre')
            order_by_sql = "ORDER BY " + ", ".join(order_parts)

            sql = f"""
                {select}
                {BASE_JOINS}
                {where_sql}
                {order_by_sql};
            """
            return dedent(sql), params

        # c) DETALLE completo
        select = SELECTS[intent].strip()
        sql = f"""
            {select}
            {BASE_JOINS}
            {where_sql}
            ORDER BY v.hora, v.id, p.nombre;
        """
        return dedent(sql), params

    # ----- Resto intents -----
    sql = f"""
        {SELECTS[intent]}
        {BASE_JOINS}
        {where_sql}
        {GROUPS[intent]};
    """
    return dedent(sql), params