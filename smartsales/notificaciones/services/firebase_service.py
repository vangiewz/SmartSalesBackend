"""
Servicio para enviar notificaciones push mediante Firebase Cloud Messaging
"""
import os
import json
import logging
import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)


class FirebaseService:
    """
    Servicio para gestionar el envío de notificaciones push a través de Firebase
    """
    _app = None

    @classmethod
    def initialize(cls):
        """
        Inicializa Firebase Admin SDK si aún no está inicializado
        """
        if cls._app is None:
            try:
                firebase_json_str = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')
                if not firebase_json_str:
                    raise ValueError("FIREBASE_SERVICE_ACCOUNT_JSON no está configurado en .env")
                
                # Parsear el JSON de las credenciales
                firebase_credentials = json.loads(firebase_json_str)
                
                cred = credentials.Certificate(firebase_credentials)
                cls._app = firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK inicializado correctamente")
            except ValueError as ve:
                logger.error(f"Error al inicializar Firebase: {ve}")
                raise
            except Exception as e:
                logger.error(f"Error inesperado al inicializar Firebase: {e}")
                raise

    @classmethod
    def enviar_notificacion(cls, token_dispositivo, titulo, cuerpo, datos=None):
        """
        Envía una notificación push a un dispositivo específico
        
        Args:
            token_dispositivo (str): Token FCM del dispositivo
            titulo (str): Título de la notificación
            cuerpo (str): Cuerpo de la notificación
            datos (dict): Datos adicionales para la notificación
            
        Returns:
            tuple: (success: bool, message: str, response: str)
        """
        cls.initialize()
        
        try:
            # Construir el mensaje
            message = messaging.Message(
                notification=messaging.Notification(
                    title=titulo,
                    body=cuerpo,
                ),
                data=datos or {},
                token=token_dispositivo,
            )
            
            # Enviar el mensaje
            response = messaging.send(message)
            logger.info(f"Notificación push enviada exitosamente: {response}")
            return True, "Notificación enviada exitosamente", response
            
        except messaging.UnregisteredError:
            logger.warning(f"Token no registrado o expirado: {token_dispositivo[:20]}...")
            return False, "Token no registrado o expirado", None
            
        except messaging.SenderIdMismatchError:
            logger.error(f"Error de Sender ID para token: {token_dispositivo[:20]}...")
            return False, "Error de configuración del remitente", None
            
        except Exception as e:
            logger.error(f"Error al enviar notificación push: {e}")
            return False, f"Error: {str(e)}", None

    @classmethod
    def enviar_notificaciones_multiples(cls, tokens, titulo, cuerpo, datos=None):
        """
        Envía una notificación push a múltiples dispositivos
        
        Args:
            tokens (list): Lista de tokens FCM
            titulo (str): Título de la notificación
            cuerpo (str): Cuerpo de la notificación
            datos (dict): Datos adicionales
            
        Returns:
            dict: Resultados del envío (exitosos, fallidos)
        """
        cls.initialize()
        
        if not tokens:
            return {'success_count': 0, 'failure_count': 0}
        
        try:
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=titulo,
                    body=cuerpo,
                ),
                data=datos or {},
                tokens=tokens,
            )
            
            response = messaging.send_multicast(message)
            logger.info(f"Notificaciones enviadas: {response.success_count} exitosas, {response.failure_count} fallidas")
            
            return {
                'success_count': response.success_count,
                'failure_count': response.failure_count,
                'responses': response.responses
            }
            
        except Exception as e:
            logger.error(f"Error al enviar notificaciones múltiples: {e}")
            return {'success_count': 0, 'failure_count': len(tokens), 'error': str(e)}
