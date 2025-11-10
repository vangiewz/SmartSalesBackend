# smartsales/garantia/services.py
from typing import Optional, Dict, Any
from smartsales.garantia import messages as MSG
from smartsales.garantia.repository import (
    get_venta_usuario_id, get_detalleventa, insert_garantia,
    get_garantia, get_garantia_detalle, set_garantia_estado, get_producto_stock, descontar_stock,
    list_garantias, get_producto_info, get_producto_vendedor_id
)

# Para URL pública de imagen de producto (si el front la usa)
try:
    from smartsales.gestionproducto.storage import public_url
except Exception:
    def public_url(_): return ""

def crear_reclamo(user_id: str, venta_id: int, producto_id: int, cantidad: int, motivo: str) -> Dict[str, Any]:
    # 1) Propiedad de la venta
    owner = get_venta_usuario_id(venta_id)
    if not owner or str(owner) != str(user_id):
        raise ValueError(MSG.ERR_NOT_OWNER)

    # 2) Detalle + vigencia
    detalle = get_detalleventa(venta_id, producto_id)
    if not detalle:
        raise ValueError(MSG.ERR_DETAIL_NOT_FOUND)
    cantidad_comprada, limite = detalle

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    if not (now <= limite):
        raise ValueError(MSG.ERR_OUT_OF_WINDOW.format(fecha=limite.isoformat()))

    # 3) Cantidad (tope por reclamo; no acumulamos entre reclamos)
    if cantidad <= 0 or cantidad > cantidad_comprada:
        raise ValueError(MSG.ERR_INVALID_QTY.format(max=cantidad_comprada))

    gid = insert_garantia(venta_id, producto_id, cantidad, motivo)

    # 4) Payload
    _stock, nombre, img_key = get_producto_info(producto_id) or (0, "", "")
    return {
        "venta_id": venta_id,
        "producto_id": producto_id,
        "garantia_id": gid,
        "estado": "Pendiente",
        "cantidad": cantidad,
        "motivo": motivo,
        "hora": None,  # se devuelve en list/detalle
        "reemplazo": None,
        "producto_nombre": nombre,
        "producto_imagen_url": public_url(img_key) if img_key else "",
        "limitegarantia": limite,
    }

def detalle_garantia(user_id: str, scope: str, venta_id: int, producto_id: int, garantia_id: int) -> Dict[str, Any]:
    """Obtiene el detalle completo de una garantía"""
    # Verificar permisos si scope es 'own'
    if scope == "own":
        owner = get_venta_usuario_id(venta_id)
        if not owner or str(owner) != str(user_id):
            raise ValueError(MSG.ERR_NOT_FOUND)
    
    row = get_garantia_detalle(venta_id, producto_id, garantia_id)
    if not row:
        raise ValueError(MSG.ERR_NOT_FOUND)
    
    (garantia_id, venta_id, producto_id, producto_nombre, imagen_key, producto_descripcion,
     producto_garantia_dias, fecha_venta, fecha_solicitud, limite_garantia, estado, motivo,
     cantidad, evaluacion, comentario_tecnico, fecha_evaluacion, tecnico_id, tecnico_nombre,
     es_reemplazo, cliente_nombre, cliente_email, cliente_telefono) = row
    
    return {
        "garantia_id": garantia_id,
        "venta_id": venta_id,
        "producto_id": producto_id,
        "producto_nombre": producto_nombre,
        "producto_imagen_url": public_url(imagen_key) if imagen_key else "",
        "producto_descripcion": producto_descripcion or "",
        "producto_garantia_dias": producto_garantia_dias,
        "fecha_venta": fecha_venta,
        "fecha_solicitud": fecha_solicitud,
        "limite_garantia": limite_garantia,
        "estado": estado,
        "motivo": motivo,
        "cantidad": cantidad,
        "evaluacion": evaluacion,
        "comentario_tecnico": comentario_tecnico or "",
        "fecha_evaluacion": fecha_evaluacion,
        "tecnico_id": tecnico_id,
        "tecnico_nombre": tecnico_nombre or "",
        "es_reemplazo": es_reemplazo,
        "cliente_nombre": cliente_nombre,
        "cliente_email": cliente_email,
        "cliente_telefono": cliente_telefono or ""
    }

def evaluar_reclamo(tecnico_id: str, venta_id: int, producto_id: int, garantia_id: int, reemplazo: Optional[bool]) -> Dict[str, Any]:
    g = get_garantia(venta_id, producto_id, garantia_id)
    if not g:
        raise ValueError(MSG.ERR_NOT_FOUND)
    _id, _estado_id, estado_nombre, cantidad, motivo, hora, rep_actual = g
    if estado_nombre != "Pendiente":
        raise ValueError(MSG.ERR_NOT_PENDING)

    # Rechazo
    if reemplazo is None:
        set_garantia_estado(venta_id, producto_id, garantia_id, "Rechazado", None)
        _enviar_notificacion_garantia(venta_id, producto_id, garantia_id)
        return _payload_from_db(venta_id, producto_id, garantia_id)

    # Reparación (no stock)
    if reemplazo is False:
        set_garantia_estado(venta_id, producto_id, garantia_id, "Completado", False)
        _enviar_notificacion_garantia(venta_id, producto_id, garantia_id)
        return _payload_from_db(venta_id, producto_id, garantia_id)

    # Reemplazo (validar stock y descontar)
    stock = get_producto_stock(producto_id)
    if stock is None or stock < cantidad:
        raise ValueError(MSG.ERR_NO_STOCK)
    descontar_stock(producto_id, cantidad)
    
    # Verificar si el stock quedó bajo (≤ 7) y notificar al vendedor
    stock_restante = get_producto_stock(producto_id)
    if stock_restante is not None and stock_restante <= 7:
        try:
            from smartsales.notificaciones.services.notificacion_manager import NotificacionManager
            from smartsales.garantia.repository import get_producto_vendedor_id
            vendedor_id = get_producto_vendedor_id(producto_id)
            if vendedor_id:
                producto_info = get_producto_info(producto_id)
                if producto_info:
                    _stock, nombre_producto, _img = producto_info
                    NotificacionManager.notificar_stock_bajo(
                        vendedor_id=str(vendedor_id),
                        producto_id=producto_id,
                        producto_nombre=nombre_producto,
                        stock_actual=stock_restante
                    )
        except Exception as e:
            # No fallar si la notificación falla
            print(f"Error al notificar stock bajo en garantía: {e}")
    
    set_garantia_estado(venta_id, producto_id, garantia_id, "Completado", True)
    _enviar_notificacion_garantia(venta_id, producto_id, garantia_id)

    return _payload_from_db(venta_id, producto_id, garantia_id)

def _payload_from_db(venta_id: int, producto_id: int, garantia_id: int) -> Dict[str, Any]:
    g = get_garantia(venta_id, producto_id, garantia_id)
    gid, _estado_id, estado, cantidad, motivo, hora, reemplazo = g
    dv = get_detalleventa(venta_id, producto_id)
    _stock, nombre, img_key = get_producto_info(producto_id) or (0, "", "")
    return {
        "venta_id": venta_id,
        "producto_id": producto_id,
        "garantia_id": gid,
        "estado": estado,
        "cantidad": cantidad,
        "motivo": motivo,
        "hora": hora,
        "reemplazo": reemplazo,
        "producto_nombre": nombre,
        "producto_imagen_url": public_url(img_key) if img_key else "",
        "limitegarantia": dv[1] if dv else None,
    }

def listar(user_id: Optional[str], scope: str, filtros: dict) -> Dict[str, Any]:
    scope_user = user_id if scope == "own" else None
    total, rows = list_garantias(
        scope_user_id=scope_user,
        estado=filtros.get("estado"),
        venta_id=filtros.get("venta_id"),
        producto_id=filtros.get("producto_id"),
        desde=filtros.get("desde"),
        hasta=filtros.get("hasta"),
        q=filtros.get("q"),
        cliente=filtros.get("cliente"),
        page=filtros.get("page", 1),
        page_size=filtros.get("page_size", 20),
    )

    # Para URL pública de imagen de producto (si UI la usa)
    try:
        from smartsales.gestionproducto.storage import public_url as _pub
    except Exception:
        def _pub(_): return ""

    results = []
    for (venta_id, producto_id, garantia_id, estado, cantidad, motivo, hora,
         reemplazo, producto_nombre, imagen_key, limite) in rows:
        results.append({
            "venta_id": venta_id,
            "producto_id": producto_id,
            "garantia_id": garantia_id,
            "estado": estado,
            "cantidad": cantidad,
            "motivo": motivo,
            "hora": hora,
            "reemplazo": reemplazo,
            "producto_nombre": producto_nombre,
            "producto_imagen_url": _pub(imagen_key) if imagen_key else "",
            "limitegarantia": limite,
        })
    return {"count": total, "results": results}


def _enviar_notificacion_garantia(venta_id: int, producto_id: int, garantia_id: int):
    """
    Función helper para enviar notificaciones cuando cambia el estado de una garantía
    """
    try:
        from smartsales.notificaciones.services import NotificacionManager
        from smartsales.models import Garantia, Venta
        from django.db import connection
        
        # Obtener la garantía usando raw SQL (ya que el modelo usa PK compuesta)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT g.id, g.venta_id, g.producto_id, g.estadogarantia_id, g.hora
                FROM garantia g
                WHERE g.venta_id = %s AND g.producto_id = %s AND g.id = %s
                """,
                [venta_id, producto_id, garantia_id]
            )
            row = cursor.fetchone()
            
            if not row:
                print(f"[NOTIF] No se pudo encontrar garantía {garantia_id}")
                return
            
            # Obtener la venta para obtener el usuario_id
            try:
                venta = Venta.objects.get(id=venta_id)
            except Venta.DoesNotExist:
                print(f"[NOTIF] No se pudo encontrar venta {venta_id}")
                return
            
            # Crear objeto garantía simulado para pasar al manager
            class GarantiaSimulada:
                def __init__(self, data):
                    self.id = data[0]
                    self.venta_id = data[1]
                    self.producto_id = data[2]
                    self.estadogarantia_id = data[3]
                    self.hora = data[4]
            
            garantia_obj = GarantiaSimulada(row)
            
            # Enviar notificación
            NotificacionManager.notificar_cambio_garantia(garantia_obj, venta)
            print(f"[NOTIF] Notificación de garantía enviada para garantía {garantia_id}")
    
    except Exception as e:
        print(f"[NOTIF] Error al enviar notificación de garantía: {e}")
        # No re-lanzar la excepción para no afectar el flujo principal
