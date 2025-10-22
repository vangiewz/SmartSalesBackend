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

INTENT_SYNONYMS = [
    ('ventas_por_mes',       [r'venta[s]? por mes', r'por mes', r'mensual']),
    ('ventas_por_marca',     [r'\bpor marca\b', r'\bmarca[s]?\b']),
    ('ventas_por_categoria', [r'\bpor categor[ií]a\b', r'\bcategor[ií]as?\b|\btipo\b']),
    ('top_productos',        [r'\btop\b', r'm[aá]s vendidos?', r'productos m[aá]s vendidos']),
    ('ventas_por_cliente',   [r'\bpor cliente\b', r'\bclientes?\b']),
    ('ticket_promedio',      [r'ticket promedio', r'ticket medio', r'\bpromedio\b']),
    ('garantias_por_estado', [r'\bgarant[ií]as?\b', r'\brma\b', r'devoluciones?']),
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

# ---------- helpers entidades ----------
STOP = {
    'entre','desde','hasta','q1','q2','q3','q4','t1','t2','t3','t4',
    'trimestre','cuatrimestre','semestre','año','anio','este','último','ultimo'
}
def _extract_quoted(text: str):
    return re.findall(r'["\']([^"\']+)["\']', text)

def _clean(s: str):
    if s is None:
        return ""
    return s.strip(" ,.;:-_")


def extract_filters(text: str):
    original = text or ""           # ← texto original (con mayúsculas)
    lower    = original.lower()     # ← copia en minúsculas para regex
    filters = {}

    # 1) entre comillas (producto)
    q = _extract_quoted(original)
    if q:
        filters['producto'] = q[0]

    # 2) spaCy (case-insensitive por el ruler)
    ner = spacy_extract(original)   # ← pásale el original
    filters.update({k:v for k,v in ner.items() if v})

    # 3) Normalización fuzzy hacia catálogos
    for k in ('marca','categoria','producto','cliente'):
        if k in filters:
            norm = fuzzy_find(k, filters[k])
            if norm: filters[k] = norm

    # 4) Patrones como respaldo (haz el match en lower pero recorta del original)
    def grab(label_regex: str):
        pat = rf'(?:de\s+la\s+|de\s+|por\s+)?(?:{label_regex})\s+(?P<v>.+?)(?=$|\s+(?:y|e|o|u)\s+|,|\.| en )'
        m = re.search(pat, lower)
        if not m: return None
        start, end = m.start('v'), m.end('v')
        val = original[start:end]          # ← corta del original (con mayúsculas)
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
    text = (prompt or '').lower()

    # 0) intent por modelo (si existe)
    ml_label, conf = _intent_by_model(text)
    intent = ml_label if ml_label and conf >= 0.65 else 'ventas_por_mes'
    if intent == 'ventas_por_mes':
        for key, pats in INTENT_SYNONYMS:
            if any(re.search(p, text) for p in pats):
                intent = key
                break

    # 1) fechas: primero intenta dateparser (muy flexible)
    span = parse_span(text)
    if span:
        start, end = span
        masked = text
        # quita años y números detectables para que no contaminen entidades
        masked = re.sub(r'\d{4}-\d{2}-\d{2}', ' ', masked)
        masked = re.sub(r'\b(20\d{2}|\d{2})\b', ' ', masked)
        masked = re.sub(r'\s{2,}', ' ', masked)
        return {'intent': intent, 'start': start, 'end': end, 'filters': extract_filters(masked), 'raw': text}

    # 2) fallback: reglas de meses/trimestres
    # 2a) rango ISO explícito
    m = re.search(r'(\d{4}-\d{2}-\d{2}).*?(\d{4}-\d{2}-\d{2})', text)
    if m:
        s = date.fromisoformat(m.group(1))
        e = date.fromisoformat(m.group(2)) + timedelta(days=1)
        masked = text.replace(m.group(1),'').replace(m.group(2),'')
        return {'intent': intent, 'start': s, 'end': e, 'filters': extract_filters(masked), 'raw': text}

    # 2b) meses (uno o varios)
    mm = re.findall(r'\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\b\s*(\d{2,4})?', text)
    if mm:
        def year_from():
            for _,y in mm:
                if y:
                    y = int(y); return y if y>100 else 2000+y
            m4 = re.search(r'\b(20\d{2})\b', text)
            return int(m4.group(1)) if m4 else date.today().year
        yy = year_from()
        m1 = SPANISH_MONTHS[mm[0][0]]; m2 = SPANISH_MONTHS[mm[-1][0]]
        s = month_start(yy, m1); e = month_end(yy, m2)
        masked = text
        for mon,y in mm:
            masked = re.sub(rf'\b{mon}\b',' ',masked)
            if y: masked = masked.replace(y,' ')
        masked = re.sub(r'\s{2,}',' ',masked)
        return {'intent': intent, 'start': s, 'end': e, 'filters': extract_filters(masked), 'raw': text}

    # 2c) trimestres/cuatrimestres/semestres/año
    today = date.today()
    s, e = today - timedelta(days=180), today + timedelta(days=1)
    m = re.search(r'(q|t|trimestre|cuatrimestre|semestre)\s*([1-4])?\s*(\d{4})?', text)
    if m:
        per, num, yy = m.groups()
        yy = int(yy) if yy else today.year
        if per.startswith('q') or 'trimestre' in per:
            q = int(num) if num else 1
            s = date(yy, 3*(q-1)+1, 1)
            e = date(yy+(q==4), 3*(q-1)+4 if q<4 else 1, 1)
        elif 'cuatrimestre' in per:
            c = int(num) if num else 1
            s = date(yy, 4*(c-1)+1, 1)
            e = date(yy+(c==3), 4*(c-1)+5 if c<3 else 1, 1)
        elif 'semestre' in per:
            s1 = int(num) if num else 1
            s = date(yy, 6*(s1-1)+1, 1)
            e = date(yy+(s1==2), 6*(s1-1)+7 if s1<2 else 1, 1)
        else:
            s, e = date(yy,1,1), date(yy+1,1,1)
        masked = text.replace(m.group(0), '')
        return {'intent': intent, 'start': s, 'end': e, 'filters': extract_filters(masked), 'raw': text}

    # 3) default: últimos 180 días
    return {'intent': intent, 'start': s, 'end': e, 'filters': extract_filters(text), 'raw': text}
