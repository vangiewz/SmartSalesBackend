import re
from datetime import date, timedelta
from calendar import monthrange
from pathlib import Path
from joblib import load

from .timeparse import parse_span
from .entities import fuzzy_find
from .spacy_ner import extract as spacy_extract

# ---------- meses (para fallback de reglas) ----------
SPANISH_MONTHS = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'setiembre': 9,
    'octubre': 10, 'noviembre': 11, 'diciembre': 12
}

def month_start(y, m): return date(y, m, 1)
def month_end(y, m):
    _, last = monthrange(y, m)
    return date(y, m, last) + timedelta(days=1)

# ---------- sinónimos por intent ----------
INTENT_SYNONYMS = [
    ('ventas_por_mes',       [r'venta[s]? por mes', r'\bpor mes\b', r'\bmensual\b']),
    ('ventas_por_marca',     [r'\bpor marca\b', r'\bmarca[s]?\b']),
    ('ventas_por_categoria', [r'\bpor categor[ií]a\b', r'\bcategor[ií]as?\b', r'\btipo\b']),
    ('top_productos',        [r'\btop\b', r'm[aá]s vendidos?', r'productos m[aá]s vendidos']),
    ('ventas_por_cliente',   [r'\bpor cliente\b', r'\bclientes?\b']),
    ('ticket_promedio',      [r'ticket promedio', r'ticket medio', r'\bpromedio\b']),
    ('garantias_por_estado', [r'\bgarant[ií]as?\b', r'\brma\b', r'devoluciones?']),
    # términos que suelen activar detalle
    ('ventas_detalladas',    [
        r'\bdetalle\b', r'\bdetallad', r'\blista\b', r'\blineas?\b',
        r'\bproducto\b', r'\bmarca\b', r'\bcategor', r'\bcliente\b',
        r'\bcantidad\b', r'\bprecio\b', r'\bgarant(ia|ías)\b'
    ]),
]

# ---------- intent classifier opcional (scikit-learn) ----------
_INTENT_CLF = None
def _load_intent_model():
    global _INTENT_CLF
    if _INTENT_CLF is None:
        p = Path(__file__).resolve().parent.parent / "models" / "intent_clf.joblib"
        if p.exists():
            _INTENT_CLF = load(p.as_posix())
    return _INTENT_CLF

def _intent_by_model(text: str):
    model = _load_intent_model()
    if not model: return None, 0.0
    try:
        proba = model.predict_proba([text])[0]
        idx = proba.argmax()
        return model.classes_[idx], float(proba[idx])
    except Exception:
        label = model.predict([text])[0]
        return label, 0.65

# ---------- normalización ----------
def _strip_accents(s: str) -> str:
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', s or '') if unicodedata.category(c) != 'Mn')

def _norm(s: str) -> str:
    return _strip_accents(s).lower().strip()

def _extract_quoted(text: str):
    return re.findall(r'["\']([^"\']+)["\']', text or "")

def _clean(s: str):
    if s is None:
        return ""
    return s.strip(" ,.;:-_")

# ---------- extracción columnas / formato / agrupación ----------
_COL_PATTERNS = [
    r'debe(?:n)? mostrar(?:se)?\s+(.+?)(?:\.|;|$)',
    r'que muestre(?:n)?\s+(.+?)(?:\.|;|$)',
    r'mostrar\s+(.+?)(?:\.|;|$)',
    r'columnas?\s+(.+?)(?:\.|;|$)',
    r'campos?\s+(.+?)(?:\.|;|$)',
    r'debe incluir\s+(.+?)(?:\.|;|$)',
]

def _normalize_requested_token(x: str) -> str:
    # determinantes y frases comunes
    x = re.sub(r'\b(el|la|los|las|de|del|un|una|unos|unas|al|por|para)\b', ' ', x, flags=re.IGNORECASE)
    x = re.sub(r'\bnombre\s+del?\s+cliente\b', 'cliente', x, flags=re.IGNORECASE)
    x = re.sub(r'\bnombre\s+cliente\b', 'cliente', x, flags=re.IGNORECASE)

    # rango de fechas / periodo
    x = re.sub(r'\brango\s+de\s+fechas\b|\brango\s+fechas\b|\bper[ií]odo\b', 'rango_fechas', x, flags=re.IGNORECASE)

    # cantidad de compras (con o sin "de" y opcional "que realizó/hizo")
    x = re.sub(r'\b(cantidad|numero|n[uú]mero)(\s+de)?\s+compras(\s+que\s+(realiz[oó]|hiz[oó]))?\b', 'n_compras', x, flags=re.IGNORECASE)

    # monto total que pagó
    x = re.sub(r'\bmonto\s+total(\s+que\s+pag[oó])?\b|\btotal\s+pagado\b|\bimporte\s+total\b', 'monto_total', x, flags=re.IGNORECASE)

    # mes → clave posible de agrupado
    x = re.sub(r'\bmes(es)?\b', 'mes', x, flags=re.IGNORECASE)

    return _norm(' '.join(x.split()))

def extract_requested_columns_from_prompt(prompt: str) -> list:
    """Extrae columnas pedidas; lista normalizada (minúsculas, sin acentos) con tokens canónicos."""
    original = prompt or ""
    p = _norm(original)

    for pat in _COL_PATTERNS:
        m = re.search(pat, p)
        if not m:
            continue
        raw = m.group(1) or ""
        # Evita arrastrar conectores
        clipped = re.split(r'\s+(en|por|con|para|agrupado|ordenado|filtrado)\b', raw)[0] or raw
        parts = re.split(r',|\s+y\s+|\s+e\s+', clipped)
        parts = [t for t in (part.strip() for part in parts) if t]
        cleaned = []
        for x in parts:
            nx = _normalize_requested_token(x)
            if nx:
                cleaned.append(nx)
        # únicos preservando orden
        out = []
        for c in cleaned:
            if c not in out:
                out.append(c)
        return out
    return []

def extract_format_from_prompt(prompt: str):
    p = _norm(prompt or "")
    if re.search(r'\bpdf\b', p): return 'pdf'
    if re.search(r'\bexcel\b|\bxlsx\b', p): return 'xlsx'
    if re.search(r'\bcsv\b', p): return 'csv'
    return None

def extract_group_by_from_prompt(prompt: str):
    """Devuelve 'producto' | 'marca' | 'categoria' | 'cliente' | 'mes' o None."""
    p = _norm(prompt or "")
    m = re.search(r'agrupad[oa]\s+por\s+(producto|marca|categor[ií]a|cliente|mes)\b', p)
    if not m:
        m = re.search(r'agrupad[oa].+?por\s+(producto|marca|categor[ií]a|cliente|mes)\b', p)
    if m:
        val = m.group(1)
        if val.startswith('categor'):
            return 'categoria'
        return val
    return None

def _infer_group_by_from_columns(cols: list[str]) -> str | None:
    """Si el usuario no dijo 'agrupado por ...', pero pidió columnas típicas de agregados, inferir clave."""
    if not cols:
        return None
    s = set(cols)
    has_agg = any(t in s for t in ('n_compras', 'monto_total', 'monto', 'total', 'total_venta'))
    if not has_agg:
        return None
    for key in ('cliente', 'producto', 'marca', 'categoria', 'mes'):
        if key in s:
            return 'categoria' if key == 'categoria' else key
    return None

def _strip_column_and_group_phrases(prompt: str) -> str:
    """Elimina directivas de columnas y 'agrupado por ...' para no contaminar filtros."""
    txt = prompt or ""
    for pat in _COL_PATTERNS:
        txt = re.sub(pat, ' ', txt, flags=re.IGNORECASE)
    txt = re.sub(r'agrupad[oa]\s+por\s+[^.,;]+', ' ', txt, flags=re.IGNORECASE)
    return txt

# ---------- soporte para fechas LATAM (DD/MM/AAAA o DD-MM-AAAA) ----------
_LATAM_DATE = r'(?P<d>\d{1,2})[/-](?P<m>\d{1,2})[/-](?P<y>\d{2,4})'
_LATAM_RANGE = rf'(?P<d1>\d{{1,2}})[/-](?P<m1>\d{{1,2}})[/-](?P<y1>\d{{2,4}})\s*(?:al|a|hasta|–|—|-|y)\s*(?P<d2>\d{{1,2}})[/-](?P<m2>\d{{1,2}})[/-](?P<y2>\d{{2,4}})'

def _parse_latam_date_str(s: str) -> date | None:
    if not s: return None
    m = re.match(_LATAM_DATE+r'$', s.strip())
    if not m: return None
    d = int(m.group('d')); mm = int(m.group('m')); yy = int(m.group('y'))
    if yy < 100:
        # Heurística simple: 00-49 => 2000+, 50-99 => 1900+
        yy = 2000 + yy if yy <= 49 else 1900 + yy
    try:
        return date(yy, mm, d)
    except ValueError:
        return None

def _extract_latam_range(original: str):
    """Devuelve (start_date, end_date_exclusive, texto_sin_fechas) si detecta un rango LATAM; si no, (None, None, original)."""
    m = re.search(_LATAM_RANGE, original, flags=re.IGNORECASE)
    if not m:
        return None, None, original
    d1 = f"{m.group('d1')}/{m.group('m1')}/{m.group('y1')}"
    d2 = f"{m.group('d2')}/{m.group('m2')}/{m.group('y2')}"
    s = _parse_latam_date_str(d1); e = _parse_latam_date_str(d2)
    if not s or not e:
        return None, None, original
    if e < s:
        s, e = e, s
    e_excl = e + timedelta(days=1)
    # Elimina el rango detectado del texto
    cleaned = original[:m.start()] + " " + original[m.end():]
    return s, e_excl, cleaned

def _extract_latam_single(original: str):
    """Devuelve (start_date, end_date_exclusive, texto_sin_fecha) si detecta una sola fecha LATAM; si no, (None, None, original)."""
    m = re.search(_LATAM_DATE, original)
    if not m:
        return None, None, original
    ds = m.group(0)
    s = _parse_latam_date_str(ds)
    if not s:
        return None, None, original
    e_excl = s + timedelta(days=1)
    cleaned = original[:m.start()] + " " + original[m.end():]
    return s, e_excl, cleaned

# ---------- helpers entidades ----------
STOP = {
    'entre','desde','hasta','q1','q2','q3','q4','t1','t2','t3','t4',
    'trimestre','cuatrimestre','semestre','año','anio','este','último','ultimo'
}

def extract_filters(text: str):
    original = text or ""
    lower    = original.lower()
    filters = {}

    # 1) entre comillas
    q = _extract_quoted(original)
    if q:
        filters['producto'] = q[0]

    # 2) spaCy
    ner = spacy_extract(original)
    filters.update({k: v for k, v in ner.items() if v})

    # 3) fuzzy
    for k in ('marca','categoria','producto','cliente'):
        if k in filters:
            norm = fuzzy_find(k, filters[k])
            if norm: filters[k] = norm

    # 4) respaldo regex con preposiciones controladas
    def grab(label_regex: str):
        pat = rf'(?:\bde la\b|\bde\b|\bdel\b|\bpor\b|\bpara\b)\s+(?:{label_regex})\s+(?P<v>.+?)(?=$|\s+(?:y|e|o|u)\s+|,|\.|\s+en\s+)'
        m = re.search(pat, lower)
        if not m: return None
        start, end = m.start('v'), m.end('v')
        val = original[start:end]
        val = _clean(val)
        if not val: return None
        return val

    if 'marca' not in filters:
        v = grab(r'\bmarca\b|\bmarcas\b')
        if v: filters['marca'] = fuzzy_find('marca', v) or v
    if 'categoria' not in filters:
        v = grab(r'\bcategor[ií]a\b|\btipo\b')
        if v: filters['categoria'] = fuzzy_find('categoria', v) or v
    if 'producto' not in filters:
        v = grab(r'\bproducto\b|\bmodelo\b')
        if v: filters['producto'] = fuzzy_find('producto', v) or v
    if 'cliente' not in filters:
        v = grab(r'\bcliente\b|\busuario\b')
        if v: filters['cliente'] = fuzzy_find('cliente', v) or v

    return filters

# ---------- NLU principal ----------
def detect_intent(prompt: str):
    original = (prompt or '')
    text = original.lower()

    today = date.today()
    default_start = today - timedelta(days=180)
    default_end   = today + timedelta(days=1)

    # 0) intent por modelo
    ml_label, conf = _intent_by_model(text)
    intent = ml_label if ml_label and conf >= 0.65 else 'ventas_por_mes'

    # 0.1) fuerza detalle si hay términos de detalle
    detalle_terms = [p for key, pats in INTENT_SYNONYMS if key == 'ventas_detalladas' for p in pats]
    if any(re.search(p, text) for p in detalle_terms):
        intent = 'ventas_detalladas'

    # 0.2) otros sinónimos
    if intent != 'ventas_detalladas':
        for key, pats in INTENT_SYNONYMS:
            if any(re.search(p, text) for p in pats):
                intent = key
                break

    # Directivas adicionales
    req_cols = extract_requested_columns_from_prompt(original)
    fmt      = extract_format_from_prompt(original)
    grp      = extract_group_by_from_prompt(original) or _infer_group_by_from_columns(req_cols)

    # si hay agrupación explícita o inferida, usamos ventas_detalladas con agregación
    if grp:
        intent = 'ventas_detalladas'

    # Limpiamos directivas antes de extraer filtros
    text_for_filters = _strip_column_and_group_phrases(original)

    # 1) Soporte explícito para formato LATAM DD/MM/AAAA (rango o única)
    # 1a) rango DD/MM/AAAA ... DD/MM/AAAA
    s_latam, e_latam, cleaned_after_range = _extract_latam_range(text_for_filters)
    if s_latam and e_latam:
        filters = extract_filters(cleaned_after_range)
        if req_cols: filters['_columns'] = req_cols
        if fmt:      filters['_format']  = fmt
        if grp:      filters['_group_by'] = grp
        if intent != 'ventas_detalladas' and any(k in filters for k in ('producto','marca','categoria','cliente')):
            intent = 'ventas_detalladas'
        return {'intent': intent, 'start': s_latam, 'end': e_latam, 'filters': filters, 'raw': text}

    # 1b) una sola fecha DD/MM/AAAA → ese día
    s1, e1, cleaned_after_single = _extract_latam_single(text_for_filters)
    if s1 and e1:
        filters = extract_filters(cleaned_after_single)
        if req_cols: filters['_columns'] = req_cols
        if fmt:      filters['_format']  = fmt
        if grp:      filters['_group_by'] = grp
        if intent != 'ventas_detalladas' and any(k in filters for k in ('producto','marca','categoria','cliente')):
            intent = 'ventas_detalladas'
        return {'intent': intent, 'start': s1, 'end': e1, 'filters': filters, 'raw': text}

    # 2) fechas: intenta dateparser (muy flexible)
    span = parse_span(text)
    if span:
        start, end = span
        filters = extract_filters(text_for_filters)
        if req_cols: filters['_columns'] = req_cols
        if fmt:      filters['_format']  = fmt
        if grp:      filters['_group_by'] = grp
        if intent != 'ventas_detalladas' and any(k in filters for k in ('producto','marca','categoria','cliente')):
            intent = 'ventas_detalladas'
        return {'intent': intent, 'start': start, 'end': end, 'filters': filters, 'raw': text}

    # 3) fallback reglas
    # 3a) rango ISO explícito
    m = re.search(r'(\d{4}-\d{2}-\d{2}).*?(\d{4}-\d{2}-\d{2})', text)
    if m:
        s = date.fromisoformat(m.group(1))
        e = date.fromisoformat(m.group(2)) + timedelta(days=1)
        base_original = original.replace(m.group(1), '').replace(m.group(2), '')
        filters = extract_filters(base_original)
        if req_cols: filters['_columns'] = req_cols
        if fmt:      filters['_format']  = fmt
        if grp:      filters['_group_by'] = grp
        if intent != 'ventas_detalladas' and any(k in filters for k in ('producto','marca','categoria','cliente')):
            intent = 'ventas_detalladas'
        return {'intent': intent, 'start': s, 'end': e, 'filters': filters, 'raw': text}

    # 3b) meses (uno o varios)
    mm = re.findall(r'\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\b\s*(\d{2,4})?', text)
    if mm:
        def year_from():
            for _, y in mm:
                if y:
                    y = int(y); return y if y > 100 else 2000 + y
            m4 = re.search(r'\b(20\d{2})\b', text)
            return int(m4.group(1)) if m4 else today.year
        yy = year_from()
        m1 = SPANISH_MONTHS[mm[0][0]]; m2 = SPANISH_MONTHS[mm[-1][0]]
        s = month_start(yy, m1); e = month_end(yy, m2)
        filters = extract_filters(text_for_filters)
        if req_cols: filters['_columns'] = req_cols
        if fmt:      filters['_format']  = fmt
        if grp:      filters['_group_by'] = grp
        if intent != 'ventas_detalladas' and any(k in filters for k in ('producto','marca','categoria','cliente')):
            intent = 'ventas_detalladas'
        return {'intent': intent, 'start': s, 'end': e, 'filters': filters, 'raw': text}

    # 3c) trimestres/cuatrimestres/semestres/año
    m = re.search(r'(q|t|trimestre|cuatrimestre|semestre)\s*([1-4])?\s*(\d{4})?', text)
    if m:
        per, num, yy = m.groups()
        yy = int(yy) if yy else today.year
        if per.startswith('q') or 'trimestre' in per:
            q = int(num) if num else 1
            s = date(yy, 3*(q-1)+1, 1)
            e = date(yy+(q==4), 3*(q-1)+4 if q < 4 else 1, 1)
        elif 'cuatrimestre' in per:
            c = int(num) if num else 1
            s = date(yy, 4*(c-1)+1, 1)
            e = date(yy+(c==3), 4*(c-1)+5 if c < 3 else 1, 1)
        elif 'semestre' in per:
            s1 = int(num) if num else 1
            s = date(yy, 6*(s1-1)+1, 1)
            e = date(yy+(s1==2), 6*(s1-1)+7 if s1 < 2 else 1, 1)
        else:
            s, e = date(yy, 1, 1), date(yy+1, 1, 1)

        filters = extract_filters(text_for_filters)
        if req_cols: filters['_columns'] = req_cols
        if fmt:      filters['_format']  = fmt
        if grp:      filters['_group_by'] = grp
        if intent != 'ventas_detalladas' and any(k in filters for k in ('producto','marca','categoria','cliente')):
            intent = 'ventas_detalladas'
        return {'intent': intent, 'start': s, 'end': e, 'filters': filters, 'raw': text}

    # 4) default: últimos 180 días
    filters = extract_filters(text_for_filters)
    if req_cols: filters['_columns'] = req_cols
    if fmt:      filters['_format']  = fmt
    if grp:      filters['_group_by'] = grp
    if intent != 'ventas_detalladas' and any(k in filters for k in ('producto','marca','categoria','cliente')):
        intent = 'ventas_detalladas'
    return {'intent': intent, 'start': default_start, 'end': default_end, 'filters': filters, 'raw': text}