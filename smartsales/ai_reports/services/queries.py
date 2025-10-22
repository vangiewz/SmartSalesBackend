from textwrap import dedent

BASE_JOINS = dedent("""
    FROM   detalleventa d
    JOIN   venta v   ON v.id = d.venta_id
    JOIN   producto p ON p.id = d.producto_id
    LEFT JOIN marca m ON m.id = p.marca_id
    LEFT JOIN tipoproducto t ON t.id = p.tipoproducto_id
    LEFT JOIN usuario u ON u.id = v.usuario_id
""")

# columnas por intent
SELECTS = {
    'ventas_por_mes':       "SELECT date_trunc('month', v.hora) AS mes, SUM(v.total) AS monto",
    'ventas_por_marca':     "SELECT m.nombre AS marca, SUM(d.cantidad*p.precio) AS monto, SUM(d.cantidad) AS unidades",
    'ventas_por_categoria': "SELECT t.nombre AS categoria, SUM(d.cantidad*p.precio) AS monto, SUM(d.cantidad) AS unidades",
    'top_productos':        "SELECT p.nombre AS producto, SUM(d.cantidad) AS unidades, SUM(d.cantidad*p.precio) AS monto",
    'ventas_por_cliente':   "SELECT u.nombre AS cliente, COUNT(v.id) AS n_ventas, SUM(v.total) AS monto",
    'ticket_promedio':      "SELECT AVG(v.total) AS ticket_promedio, COUNT(*) AS n_ventas",
    'garantias_por_estado': "SELECT e.nombre AS estado, COUNT(*) AS n_casos FROM garantia g JOIN estadogarantia e ON e.id=g.estadogarantia_id",
}

# group by por intent
GROUPS = {
    'ventas_por_mes':       "GROUP BY 1 ORDER BY 1",
    'ventas_por_marca':     "GROUP BY m.nombre ORDER BY monto DESC",
    'ventas_por_categoria': "GROUP BY t.nombre ORDER BY monto DESC",
    'top_productos':        "GROUP BY p.nombre ORDER BY unidades DESC LIMIT 10",
    'ventas_por_cliente':   "GROUP BY u.nombre ORDER BY monto DESC",
    'ticket_promedio':      "",
    'garantias_por_estado': "GROUP BY e.nombre ORDER BY n_casos DESC",
}
def build_sql(intent: str, filters: dict):
    """
    Devuelve (sql, params) con WHERE dinámico:
    - Siempre filtra por rango de fechas en v.hora o g.hora
    - Aplica filtros opcionales: producto, marca, categoria, cliente (ILIKE %...%)
    - En ventas_por_mes: si hay filtro de ítems (producto/marca/categoria) suma por líneas.
    """
    where = []
    params = []

    # fuente de fecha (venta vs garantia)
    date_col = 'v.hora' if intent != 'garantias_por_estado' else 'g.hora'

    # Rango: los dos primeros params SIEMPRE son start/end (el runner los pondrá)
    where.append(f"{date_col} >= %s AND {date_col} < %s")

    # Filtros opcionales con ILIKE
    has_item_filter = False  # producto/marca/categoria
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
            # NOTA: cliente no cuenta como "item filter"

    where_sql = "WHERE " + " AND ".join(where) if where else ""

    # ----- Intención de garantías (usa tabla g) -----
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

    # ----- Ventas por mes (select condicional) -----
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

    # ----- Resto de intenciones (usa SELECTS/GROUPS definidos) -----
    sql = f"""
        {SELECTS[intent]}
        {BASE_JOINS}
        {where_sql}
        {GROUPS[intent]};
    """
    return dedent(sql), params