import spacy
from spacy.pipeline import EntityRuler
from django.db import connection

_NLP = None
def _fetch(sql):
    with connection.cursor() as cur:
        cur.execute(sql)
        return [r[0] for r in cur.fetchall()]

def nlp():
    global _NLP
    if _NLP: return _NLP
    _NLP = spacy.load("es_core_news_sm")
    # 👇 Case-insensitive (usa atributo LOWER para matchear)
    ruler = _NLP.add_pipe(
        "entity_ruler",
        before="ner",
        config={"phrase_matcher_attr": "LOWER"}
    )
    patterns = []
    for m in _fetch("SELECT nombre FROM marca"):
        patterns.append({"label":"MARCA", "pattern": m})
    for c in _fetch("SELECT nombre FROM tipoproducto"):
        patterns.append({"label":"CATEGORIA", "pattern": c})
    for p in _fetch("SELECT nombre FROM producto"):
        patterns.append({"label":"PRODUCTO", "pattern": p})
    for u in _fetch("SELECT nombre FROM usuario"):
        patterns.append({"label":"CLIENTE", "pattern": u})
    ruler.add_patterns(patterns)
    return _NLP

def extract(text: str):
    # ⚠️ Recibe texto ORIGINAL, no lo conviertas a lower aquí
    doc = nlp()(text)
    out = {}
    for ent in doc.ents:
        if ent.label_ == "MARCA": out.setdefault("marca", ent.text)
        if ent.label_ == "CATEGORIA": out.setdefault("categoria", ent.text)
        if ent.label_ == "PRODUCTO": out.setdefault("producto", ent.text)
        if ent.label_ == "CLIENTE": out.setdefault("cliente", ent.text)
    return out
