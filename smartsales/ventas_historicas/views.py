from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.db import connection
from django.utils import timezone
from rest_framework.permissions import AllowAny
#include Response APIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import HistoricoQuerySerializer


def dictfetchall(cursor) -> List[Dict[str, Any]]:
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def to_jsonable(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def jsonify_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{k: to_jsonable(v) for k, v in row.items()} for row in rows]


GRANULARITY_MAP = {
    "day": "day",
    "week": "week",
    "month": "month",
    "quarter": "quarter",
    "year": "year",
}


def _default_bounds_from_db() -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Devuelve (min_hora, max_hora) de venta.hora como datetimes aware (UTC si USE_TZ=True).
    Si no hay datos, devuelve (None, None).
    """
    with connection.cursor() as cur:
        cur.execute("SELECT MIN(hora) AS min_hora, MAX(hora) AS max_hora FROM venta;")
        row = cur.fetchone()  # (min_hora, max_hora) ya vienen como tz-aware si timestamptz
    return row[0], row[1]


class HistoricoVentasView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = HistoricoQuerySerializer(data=request.query_params)
        qs.is_valid(raise_exception=True)
        params = qs.validated_data

        group_by = params["group_by"]
        granularity = params.get("granularity", "month")
        date_trunc_unit = GRANULARITY_MAP.get(granularity, "month")

        # 1) Resolver rango por defecto con MIN/MAX si no vienen fechas
        min_hora_db, max_hora_db = _default_bounds_from_db()

        if min_hora_db is None or max_hora_db is None:
            # No hay ventas en la BD
            return Response({
                "meta": {
                    "group_by": group_by,
                    "granularity": granularity if group_by == "periodo" else None,
                    "from": None,
                    "to": None,
                    "count": 0,
                    "generated_at": timezone.now().isoformat(),
                    "note": "Sin datos en la tabla venta",
                },
                "data": [],
            })

        # Si el usuario no manda fechas, usamos MIN/MAX reales de la BD
        date_from = params.get("date_from")
        date_to = params.get("date_to")

        if date_from is None:
            date_from_dt = min_hora_db
        else:
            # comienzo del día en zona del proyecto (aware)
            date_from_dt = timezone.make_aware(datetime.combine(date_from, datetime.min.time()))

        if date_to is None:
            # hacemos el to exclusivo sumando 1 segundo al último dato
            date_to_dt = max_hora_db + timedelta(seconds=1)
        else:
            # end exclusivo -> día siguiente 00:00
            date_to_dt = timezone.make_aware(datetime.combine(date_to, datetime.min.time())) + timedelta(days=1)

        # 2) Ejecutar consulta según group_by
        if group_by == "periodo":
            data = self._by_periodo(date_from_dt, date_to_dt, date_trunc_unit)
        elif group_by == "producto":
            limit = params.get("limit")
            offset = params.get("offset", 0)
            data = self._by_producto(date_from_dt, date_to_dt, limit, offset)
        else:  # cliente
            limit = params.get("limit")
            offset = params.get("offset", 0)
            data = self._by_cliente(date_from_dt, date_to_dt, limit, offset)

        return Response({
            "meta": {
                "group_by": group_by,
                "granularity": granularity if group_by == "periodo" else None,
                "from": date_from_dt.isoformat(),
                "to": date_to_dt.isoformat(),
                "count": len(data),
                "generated_at": timezone.now().isoformat(),
            },
            "data": jsonify_rows(data),
        })

    def _by_periodo(self, date_from_dt: datetime, date_to_dt: datetime, date_trunc_unit: str):
        """
        Devuelve SOLO periodos con datos. Sin generate_series. Sin huecos.
        Combina totales (venta) y cantidades (detalle) con FULL OUTER JOIN.
        """
        with connection.cursor() as cur:
            sql = f"""
            WITH ventas_bucket AS (
                SELECT date_trunc(%s, hora) AS bucket, SUM(total) AS total
                FROM venta
                WHERE hora >= %s AND hora < %s
                GROUP BY 1
            ),
            cantidades_bucket AS (
                SELECT date_trunc(%s, v.hora) AS bucket, SUM(dv.cantidad) AS cantidad
                FROM venta v
                JOIN detalleventa dv ON dv.venta_id = v.id
                WHERE v.hora >= %s AND v.hora < %s
                GROUP BY 1
            )
            SELECT
                COALESCE(v.bucket, c.bucket) AS period,
                COALESCE(v.total, 0)         AS total,
                COALESCE(c.cantidad, 0)      AS cantidad,
                CASE WHEN COALESCE(c.cantidad, 0) > 0
                     THEN COALESCE(v.total, 0) / COALESCE(c.cantidad, 0)
                     ELSE 0 END               AS ticket_promedio
            FROM ventas_bucket v
            FULL OUTER JOIN cantidades_bucket c
              ON v.bucket = c.bucket
            ORDER BY period ASC;
            """
            cur.execute(
                sql,
                [
                    date_trunc_unit, date_from_dt, date_to_dt,  # ventas_bucket
                    date_trunc_unit, date_from_dt, date_to_dt,  # cantidades_bucket
                ],
            )
            rows = dictfetchall(cur)
        return rows

    def _by_producto(self, date_from_dt: datetime, date_to_dt: datetime, limit: Optional[int], offset: int):
        with connection.cursor() as cur:
            base_sql = """
            SELECT
                p.id AS producto_id,
                p.nombre AS producto,
                SUM(dv.cantidad) AS cantidad,
                SUM(dv.cantidad * p.precio)::numeric(14,2) AS total
            FROM detalleventa dv
            JOIN venta v ON v.id = dv.venta_id
            JOIN producto p ON p.id = dv.producto_id
            WHERE v.hora >= %s AND v.hora < %s
            GROUP BY p.id, p.nombre
            ORDER BY total DESC
            """
            params = [date_from_dt, date_to_dt]
            if limit is not None:
                base_sql += " LIMIT %s OFFSET %s"
                params += [limit, offset]
            cur.execute(base_sql, params)
            rows = dictfetchall(cur)
        return rows

    def _by_cliente(self, date_from_dt: datetime, date_to_dt: datetime, limit: Optional[int], offset: int):
        with connection.cursor() as cur:
            base_sql = """
            WITH totales AS (
                SELECT v.usuario_id, SUM(v.total) AS total
                FROM venta v
                WHERE v.hora >= %s AND v.hora < %s
                GROUP BY v.usuario_id
            ),
            cantidades AS (
                SELECT v.usuario_id, SUM(dv.cantidad) AS cantidad
                FROM venta v
                JOIN detalleventa dv ON dv.venta_id = v.id
                WHERE v.hora >= %s AND v.hora < %s
                GROUP BY v.usuario_id
            )
            SELECT
                u.id AS cliente_id,
                u.nombre AS cliente,
                COALESCE(t.total, 0) AS total,
                COALESCE(c.cantidad, 0) AS cantidad
            FROM usuario u
            JOIN totales t ON t.usuario_id = u.id
            LEFT JOIN cantidades c ON c.usuario_id = u.id
            ORDER BY t.total DESC
            """
            params = [date_from_dt, date_to_dt, date_from_dt, date_to_dt]
            if limit is not None:
                base_sql += " LIMIT %s OFFSET %s"
                params += [limit, offset]
            cur.execute(base_sql, params)
            rows = dictfetchall(cur)
        return rows