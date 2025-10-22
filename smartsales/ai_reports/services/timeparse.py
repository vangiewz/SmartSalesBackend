from datetime import date, timedelta
from calendar import monthrange
from dateparser.search import search_dates
import dateparser

MONTH_WORDS = {
    'enero','febrero','marzo','abril','mayo','junio','julio',
    'agosto','septiembre','setiembre','octubre','noviembre','diciembre','mes'
}

def _month_span(d: date):
    last = monthrange(d.year, d.month)[1]
    return date(d.year, d.month, 1), date(d.year, d.month, last) + timedelta(days=1)

def parse_span(text: str):
    """
    Devuelve (start_date, end_exclusive) si puede inferir un rango.
    Usa español por defecto.
    """
    txt = (text or "").lower()

    # 1) dos o más fechas explícitas en el texto
    found = search_dates(txt, languages=['es'])
    if found and len(found) >= 2:
        d1 = found[0][1].date()
        d2 = found[-1][1].date()
        if d1 > d2: d1, d2 = d2, d1
        return d1, d2 + timedelta(days=1)

    # 2) una sola fecha/frase -> heurística mes/año
    d = dateparser.parse(txt, languages=['es'])
    if d:
        d = d.date()
        if any(w in txt for w in MONTH_WORDS):
            return _month_span(d)
        if 'año' in txt or 'anio' in txt:
            return date(d.year,1,1), date(d.year+1,1,1)

    return None
