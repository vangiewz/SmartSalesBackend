from django.db import connection
from .queries import build_sql

def run_sql(intent: str, start, end, filters=None):
    sql, extra = build_sql(intent, filters or {})
    params = [start, end] + extra
    with connection.cursor() as cur:
        cur.execute(sql, params)
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return {
        "intent": intent,
        "rows": rows,
        "columns": cols,
        "start": str(start),
        "end": str(end),
        "filters": filters or {}
    }
