"""
Manager para crear y gestionar notificaciones en la cola
"""
import logging
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone
from ..models import ColaNotificacion, SuscripcionMovil

logger = logging.getLogger(__name__)


class NotificacionManager:
    """
    Gestor centralizado para crear notificaciones en la cola
    """
    
    @staticmethod
    def crear_notificacion(usuario_id, titulo, cuerpo, datos=None, canales=None):
        """
        Crea notificaciones en la cola para un usuario
        
        Args:
            usuario_id (UUID): ID del usuario destinatario
            titulo (str): Título de la notificación
            cuerpo (str): Cuerpo/mensaje de la notificación
            datos (dict): Datos adicionales en formato JSON
            canales (list): Lista de canales ['WEB', 'PUSH']. Por defecto ambos.
            
        Returns:
            list: Lista de notificaciones creadas
        """
        if canales is None:
            canales = ['WEB', 'PUSH']
        
        notificaciones_creadas = []
        
        try:
            with transaction.atomic():
                for canal in canales:
                    # Para PUSH, verificar que el usuario tenga suscripción activa
                    if canal == 'PUSH':
                        tiene_suscripcion = SuscripcionMovil.objects.filter(
                            usuario_id=usuario_id,
                            activo=True
                        ).exists()
                        
                        if not tiene_suscripcion:
                            logger.warning(f"Usuario {usuario_id} no tiene suscripción móvil activa")
                            # Crear notificación con estado ERROR
                            notif = ColaNotificacion.objects.create(
                                usuario_id=usuario_id,
                                canal=canal,
                                titulo=titulo,
                                cuerpo=cuerpo,
                                datos=datos or {},
                                estado='ERROR',
                                reintentos=0,
                                max_reintentos=0,
                                proximo_intento=None
                            )
                            notificaciones_creadas.append(notif)
                            continue
                    
                    # Crear notificación pendiente
                    notif = ColaNotificacion.objects.create(
                        usuario_id=usuario_id,
                        canal=canal,
                        titulo=titulo,
                        cuerpo=cuerpo,
                        datos=datos or {},
                        estado='PENDIENTE',
                        reintentos=0,
                        max_reintentos=3,
                        proximo_intento=timezone.now()
                    )
                    notificaciones_creadas.append(notif)
                    logger.info(f"Notificación {canal} creada para usuario {usuario_id}: {titulo}")
            
            return notificaciones_creadas
            
        except Exception as e:
            logger.error(f"Error al crear notificaciones para usuario {usuario_id}: {e}")
            return []

    @staticmethod
    def notificar_compra_exitosa(venta):
        """
        Crea notificaciones cuando se realiza una compra
        
        Args:
            venta: Objeto Venta
        """
        titulo = "¡Compra Exitosa!"
        cuerpo = f"Tu compra por ${venta.total:.2f} ha sido procesada exitosamente. Gracias por tu preferencia."
        datos = {
            'tipo': 'compra',
            'venta_id': venta.id,
            'total': float(venta.total),
            'fecha': venta.hora.isoformat()
        }
        
        return NotificacionManager.crear_notificacion(
            usuario_id=venta.usuario_id,
            titulo=titulo,
            cuerpo=cuerpo,
            datos=datos
        )

    @staticmethod
    def notificar_cambio_garantia(garantia, venta):
        """
        Crea notificaciones cuando cambia el estado de una garantía
        
        Args:
            garantia: Objeto Garantia
            venta: Objeto Venta asociado
        """
        from smartsales.models import EstadoGarantia
        
        try:
            estado = EstadoGarantia.objects.get(id=garantia.estadogarantia_id)
            estado_nombre = estado.nombre
        except:
            estado_nombre = "actualizado"
        
        titulo = f"Actualización de Garantía - {estado_nombre}"
        
        if estado_nombre.lower() == 'completado':
            cuerpo = f"Tu solicitud de garantía ha sido completada exitosamente."
        elif estado_nombre.lower() == 'rechazado':
            cuerpo = f"Tu solicitud de garantía ha sido rechazada. Contacta a soporte para más información."
        else:
            cuerpo = f"El estado de tu garantía ha cambiado a: {estado_nombre}."
        
        datos = {
            'tipo': 'garantia',
            'garantia_id': garantia.id,
            'venta_id': garantia.venta_id,
            'producto_id': garantia.producto_id,
            'estado': estado_nombre,
            'fecha': garantia.hora.isoformat()
        }
        
        return NotificacionManager.crear_notificacion(
            usuario_id=venta.usuario_id,
            titulo=titulo,
            cuerpo=cuerpo,
            datos=datos
        )

    @staticmethod
    def notificar_stock_bajo(producto):
        """
        Crea notificaciones cuando el stock de un producto es bajo (≤7)
        
        Args:
            producto: Objeto Producto
        """
        if producto.stock > 7:
            return []
        
        titulo = "⚠️ Stock Bajo en Producto"
        cuerpo = f"El producto '{producto.nombre}' tiene solo {producto.stock} unidades en stock. Considera reabastecer pronto."
        datos = {
            'tipo': 'stock_bajo',
            'producto_id': producto.id,
            'producto_nombre': producto.nombre,
            'stock_actual': producto.stock,
            'fecha': timezone.now().isoformat()
        }
        
        return NotificacionManager.crear_notificacion(
            usuario_id=producto.id_vendedor,
            titulo=titulo,
            cuerpo=cuerpo,
            datos=datos
        )
