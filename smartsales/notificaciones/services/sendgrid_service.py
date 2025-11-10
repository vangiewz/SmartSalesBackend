"""
Servicio para enviar notificaciones web (email) mediante SendGrid
"""
import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

logger = logging.getLogger(__name__)


class SendGridService:
    """
    Servicio para gestionar el envío de notificaciones por correo electrónico
    """
    
    @staticmethod
    def enviar_email(destinatario_email, titulo, cuerpo_html, cuerpo_texto=None):
        """
        Envía un correo electrónico mediante SendGrid
        
        Args:
            destinatario_email (str): Email del destinatario
            titulo (str): Asunto del correo
            cuerpo_html (str): Contenido HTML del correo
            cuerpo_texto (str): Contenido en texto plano (opcional)
            
        Returns:
            tuple: (success: bool, message: str, status_code: int)
        """
        try:
            api_key = os.getenv('SENDGRID_API_KEY')
            from_email = os.getenv('SENDGRID_FROM_EMAIL')
            from_name = os.getenv('SENDGRID_FROM_NAME', 'SmartSales')
            
            if not api_key or not from_email:
                raise ValueError("Credenciales de SendGrid no configuradas en .env")
            
            # Crear el mensaje
            message = Mail(
                from_email=(from_email, from_name),
                to_emails=destinatario_email,
                subject=titulo,
                html_content=cuerpo_html,
                plain_text_content=cuerpo_texto or cuerpo_html
            )
            
            # Enviar el correo
            sg = SendGridAPIClient(api_key)
            response = sg.send(message)
            
            logger.info(f"Email enviado exitosamente a {destinatario_email}. Status: {response.status_code}")
            return True, "Email enviado exitosamente", response.status_code
            
        except Exception as e:
            logger.error(f"Error al enviar email a {destinatario_email}: {e}")
            return False, f"Error: {str(e)}", None

    @staticmethod
    def crear_html_notificacion(titulo, mensaje, tipo='info'):
        """
        Crea un template HTML simple para notificaciones
        
        Args:
            titulo (str): Título de la notificación
            mensaje (str): Mensaje de la notificación
            tipo (str): Tipo de notificación (info, success, warning, error)
            
        Returns:
            str: HTML formateado
        """
        colores = {
            'info': '#3498db',
            'success': '#2ecc71',
            'warning': '#f39c12',
            'error': '#e74c3c'
        }
        
        color = colores.get(tipo, colores['info'])
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{titulo}</title>
        </head>
        <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="background-color: {color}; color: white; padding: 20px; text-align: center;">
                    <h1 style="margin: 0; font-size: 24px;">{titulo}</h1>
                </div>
                <div style="padding: 30px; color: #333;">
                    <p style="font-size: 16px; line-height: 1.6; margin: 0;">
                        {mensaje}
                    </p>
                </div>
                <div style="background-color: #f8f8f8; padding: 15px; text-align: center; font-size: 12px; color: #666;">
                    <p style="margin: 0;">SmartSales - Sistema de Gestión de Ventas</p>
                    <p style="margin: 5px 0 0 0;">Este es un correo automático, por favor no responder.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
