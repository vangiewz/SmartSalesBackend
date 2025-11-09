# smartsales/carrito_voz/services.py

from __future__ import annotations

import re
from decimal import Decimal
from typing import Dict, List, Any
from uuid import UUID

from .repository import buscar_producto_por_fragmento
from .messages import MSG_SIN_PRODUCTOS

# Palabras de números simples en español -> cantidad
MAPA_NUMEROS = {
    "un": 1,
    "uno": 1,
    "una": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "once": 11,
    "doce": 12,
}

# Palabras que no aportan a la búsqueda del producto
STOPWORDS_BUSQUEDA = {
    "quiero",
    "quisiera",
    "deseo",
    "agrega",
    "agregar",
    "agregame",
    "añade",
    "añadir",
    "añademe",
    "pon",
    "ponme",
    "coloca",
    "compra",
    "comprar",
    "vende",
    "vender",
    "para",
    "por",
    "favor",
    "el",
    "la",
    "los",
    "las",
    "al",
    "del",
    "de",
}


def _normalizar_texto(texto: str) -> str:
    texto = texto.strip().lower()
    texto = re.sub(r"[^\w\sáéíóúüñ]", " ", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def _split_en_fragmentos(texto: str) -> List[str]:
    """
    Divide el texto original en fragmentos tipo:
    '2 televisores samsung, 1 heladera lg' -> ['2 televisores samsung', '1 heladera lg']
    usando separadores como 'y', 'más', comas, etc.
    """
    separadores = [
        ",",
        " y ",
        " e ",
        " mas ",
        " más ",
        " ademas ",
        " además ",
        " tambien ",
        " también ",
        " y un ",
        " y una ",
    ]
    fragmentos = [texto]

    for sep in separadores:
        tmp: List[str] = []
        for f in fragmentos:
            tmp.extend(f.split(sep))
        fragmentos = tmp

    fragmentos_limpios = [f.strip() for f in fragmentos if f.strip()]
    return fragmentos_limpios


def _extraer_cantidad(fragmento: str) -> int:
    """
    Busca primero números (e.g. 2, 5, 10) y si no hay,
    intenta con palabras (uno, dos, tres...). Default = 1.
    """
    match = re.search(r"\b(\d+)\b", fragmento)
    if match:
        try:
            valor = int(match.group(1))
            if valor > 0:
                return valor
        except ValueError:
            pass

    palabras = fragmento.lower().split()
    for p in palabras:
        if p in MAPA_NUMEROS:
            return MAPA_NUMEROS[p]

    return 1


def _limpiar_fragmento_para_busqueda(fragmento: str) -> str:
    """
    Quita números, palabras numéricas y stopwords (como 'quiero', 'agrega', etc.)
    para quedarse con las palabras más representativas del producto.
    """
    texto = re.sub(r"\b\d+\b", " ", fragmento.lower())
    # eliminar palabras numéricas
    for palabra in MAPA_NUMEROS.keys():
        texto = re.sub(rf"\b{palabra}\b", " ", texto, flags=re.IGNORECASE)
    # eliminar stopwords comunes
    for palabra in STOPWORDS_BUSQUEDA:
        texto = re.sub(rf"\b{palabra}\b", " ", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\s+", " ", texto).strip()

    # mantener solo las últimas 4 palabras (las más relevantes)
    palabras = texto.split()
    if len(palabras) > 4:
        texto = " ".join(palabras[-4:])

    return texto


def interpretar_texto_carrito(
    usuario_id: UUID,
    texto: str,
    limite_items: int = 10,
) -> Dict[str, Any]:
    """
    UC-11 – Armar carrito por voz — Web / Móvil
    Ahora incluye sugerencias de productos (opciones) si hay más de uno similar.
    """

    texto_original = texto
    texto = _normalizar_texto(texto)

    fragmentos = _split_en_fragmentos(texto)
    items: List[Dict[str, Any]] = []
    fragmentos_sin_match: List[str] = []

    for fragmento in fragmentos:
        if len(items) >= limite_items:
            break

        cantidad = _extraer_cantidad(fragmento)
        frag_para_busqueda = _limpiar_fragmento_para_busqueda(fragmento)

        if not frag_para_busqueda:
            fragmentos_sin_match.append(fragmento)
            continue

        productos = buscar_producto_por_fragmento(
            frag_para_busqueda,
            limite=5,
            id_vendedor=str(usuario_id),
        )
        if not productos:
            fragmentos_sin_match.append(fragmento)
            continue

        # Producto principal: el primero
        principal = productos[0]
        precio_unitario: Decimal = (
            principal["precio"]
            if isinstance(principal["precio"], Decimal)
            else Decimal(principal["precio"])
        )
        subtotal = precio_unitario * Decimal(cantidad)

        # Alternativas (resto de productos)
        alternativas = [
            {
                "producto_id": p["id"],
                "nombre": p["nombre"],
                "precio_unitario": (
                    p["precio"]
                    if isinstance(p["precio"], Decimal)
                    else Decimal(p["precio"])
                ),
            }
            for p in productos[1:]
        ]

        items.append(
            {
                "producto_id": principal["id"],
                "nombre": principal["nombre"],
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "subtotal": subtotal,
                "fragmento_voz": fragmento.strip(),
                "opciones": alternativas,
            }
        )

    total_estimado = sum((item["subtotal"] for item in items), Decimal("0.00"))

    if not items:
        return {
            "usuario_id": str(usuario_id),
            "texto": texto_original,
            "total_estimado": Decimal("0.00"),
            "items": [],
            "fragmentos_sin_match": fragmentos_sin_match,
            "mensaje": MSG_SIN_PRODUCTOS,
        }

    return {
        "usuario_id": str(usuario_id),
        "texto": texto_original,
        "total_estimado": total_estimado,
        "items": items,
        "fragmentos_sin_match": fragmentos_sin_match,
    }
