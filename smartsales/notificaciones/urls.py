"""
URLs para el sistema de notificaciones
"""
from django.urls import path
from . import views

urlpatterns = [
    # Gestión de suscripciones móviles
    path('suscripcion/actualizar-token/', views.actualizar_token_dispositivo, name='actualizar_token'),
    path('suscripcion/estado/', views.obtener_estado_suscripcion, name='estado_suscripcion'),
    path('suscripcion/desactivar/', views.desactivar_suscripcion, name='desactivar_suscripcion'),
    
    # Consulta de notificaciones
    path('mis-notificaciones/', views.listar_notificaciones_usuario, name='mis_notificaciones'),
]
