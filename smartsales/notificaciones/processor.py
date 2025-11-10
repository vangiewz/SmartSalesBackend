"""
Procesador de la cola de notificaciones
"""
import logging
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from .models import ColaNotificacion, SuscripcionMovil
from .services import FirebaseService, SendGridService

logger = logging.getLogger(__name__)


class NotificacionProcessor:
    """
    Procesador para enviar notificaciones pendientes de la cola
    """
    
    def __init__(self):
        self.firebase_service = FirebaseService
        self.sendgrid_service = SendGridService
    
    def procesar_cola(self, limite=100):
        """
        Procesa las notificaciones pendientes en la cola
        
        Args:
            limite (int): Número máximo de notificaciones a procesar
            
        Returns:
            dict: Estadísticas del procesamiento
        """
        stats = {
            'procesadas': 0,
            'exitosas': 0,
            'fallidas': 0,
            'reintentadas': 0
        }
        
        # Obtener notificaciones pendientes
        notificaciones = ColaNotificacion.objects.filter(
            estado__in=['PENDIENTE', 'REINTENTAR'],
            proximo_intento__lte=timezone.now()
        ).order_by('proximo_intento')[:limite]
        
        logger.info(f"Procesando {notificaciones.count()} notificaciones pendientes...")
        
        for notificacion in notificaciones:
            try:
                with transaction.atomic():
                    # Marcar como enviando
                    notificacion.estado = 'ENVIANDO'
                    notificacion.save(update_fields=['estado', 'actualizado_en'])
                    
                    # Procesar según el canal
                    if notificacion.canal == 'PUSH':
                        exito = self._enviar_push(notificacion)
                    elif notificacion.canal == 'WEB':
                        exito = self._enviar_web(notificacion)
                    else:
                        logger.error(f"Canal desconocido: {notificacion.canal}")
                        exito = False
                    
                    # Actualizar estado según resultado
                    if exito:
                        notificacion.estado = 'ENVIADO'
                        stats['exitosas'] += 1
                        logger.info(f"Notificación {notificacion.id} enviada exitosamente")
                    else:
                        notificacion.reintentos += 1
                        
                        if notificacion.reintentos >= notificacion.max_reintentos:
                            notificacion.estado = 'ERROR'
                            stats['fallidas'] += 1
                            logger.error(f"Notificación {notificacion.id} alcanzó máximo de reintentos")
                        else:
                            notificacion.estado = 'REINTENTAR'
                            # Próximo intento en 5 minutos * número de reintentos
                            minutos = 5 * notificacion.reintentos
                            notificacion.proximo_intento = timezone.now() + timedelta(minutes=minutos)
                            stats['reintentadas'] += 1
                            logger.warning(f"Notificación {notificacion.id} reintentará en {minutos} minutos")
                    
                    notificacion.save()
                    stats['procesadas'] += 1
                    
            except Exception as e:
                logger.error(f"Error al procesar notificación {notificacion.id}: {e}")
                try:
                    notificacion.estado = 'ERROR'
                    notificacion.save(update_fields=['estado', 'actualizado_en'])
                except:
                    pass
                stats['fallidas'] += 1
        
        logger.info(f"Procesamiento completado: {stats}")
        return stats
    
    def _enviar_push(self, notificacion):
        """
        Envía una notificación push
        
        Args:
            notificacion: Objeto ColaNotificacion
            
        Returns:
            bool: True si se envió exitosamente
        """
        try:
            # Obtener suscripción activa del usuario
            suscripcion = SuscripcionMovil.objects.filter(
                usuario_id=notificacion.usuario_id,
                activo=True
            ).first()
            
            if not suscripcion:
                logger.warning(f"Usuario {notificacion.usuario_id} no tiene suscripción activa")
                return False
            
            # Convertir datos dict a dict de strings (requerido por FCM)
            datos_str = {k: str(v) for k, v in notificacion.datos.items()}
            
            # Enviar notificación
            exito, mensaje, response = self.firebase_service.enviar_notificacion(
                token_dispositivo=suscripcion.token_dispositivo,
                titulo=notificacion.titulo,
                cuerpo=notificacion.cuerpo,
                datos=datos_str
            )
            
            # Si el token es inválido, desactivar la suscripción
            if not exito and 'no registrado' in mensaje.lower():
                suscripcion.activo = False
                suscripcion.save(update_fields=['activo', 'actualizado_en'])
                logger.warning(f"Suscripción {suscripcion.id} desactivada por token inválido")
            
            return exito
            
        except Exception as e:
            logger.error(f"Error al enviar notificación push {notificacion.id}: {e}")
            return False
    
    def _enviar_web(self, notificacion):
        """
        Envía una notificación web (email)
        
        Args:
            notificacion: Objeto ColaNotificacion
            
        Returns:
            bool: True si se envió exitosamente
        """
        try:
            # Obtener email del usuario
            from smartsales.models import Usuario
            usuario = Usuario.objects.get(id=notificacion.usuario_id)
            
            # Determinar tipo de notificación para el color del email
            tipo_email = 'info'
            if 'garantia' in notificacion.datos.get('tipo', ''):
                tipo_email = 'warning'
            elif 'compra' in notificacion.datos.get('tipo', ''):
                tipo_email = 'success'
            elif 'stock_bajo' in notificacion.datos.get('tipo', ''):
                tipo_email = 'warning'
            
            # Crear HTML del email
            html_content = self.sendgrid_service.crear_html_notificacion(
                titulo=notificacion.titulo,
                mensaje=notificacion.cuerpo,
                tipo=tipo_email
            )
            
            # Enviar email
            exito, mensaje, status_code = self.sendgrid_service.enviar_email(
                destinatario_email=usuario.correo,
                titulo=notificacion.titulo,
                cuerpo_html=html_content,
                cuerpo_texto=notificacion.cuerpo
            )
            
            return exito
            
        except Exception as e:
            logger.error(f"Error al enviar notificación web {notificacion.id}: {e}")
            return False
