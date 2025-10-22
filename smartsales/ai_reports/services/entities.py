from rapidfuzz import process, fuzz
from django.db import connection

def _fetch_list(sql):
    with connection.cursor() as cur:
        cur.execute(sql)
        return [r[0] for r in cur.fetchall()]

CAT = None
def ensure_catalogs():
    global CAT
    if CAT is None:
        CAT = {
            "marca":     _fetch_list("SELECT nombre FROM marca"),
            "categoria": _fetch_list("SELECT nombre FROM tipoproducto"),
            "producto":  _fetch_list("SELECT nombre FROM producto"),
            "cliente":   _fetch_list("SELECT nombre FROM usuario"),
        }
    return CAT

def fuzzy_find(kind: str, text: str, score_cutoff=83):
    if not text: return None
    cats = ensure_catalogs()
    choices = cats.get(kind, [])
    if not choices: return None
    match = process.extractOne(text, choices, scorer=fuzz.WRatio, score_cutoff=score_cutoff)
    return match[0] if match else None
