"""
Modelos para el sistema de notificaciones
"""
from django.db import models
from smartsales.models import Usuario


class SuscripcionMovil(models.Model):
    """
    Modelo para suscripciones de notificaciones móviles
    """
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='usuario_id')
    token_dispositivo = models.TextField(unique=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'suscripcion_movil'
        managed = False

    def __str__(self):
        return f"Suscripción {self.usuario.nombre} - {self.token_dispositivo[:20]}..."


class ColaNotificacion(models.Model):
    """
    Modelo para la cola de notificaciones pendientes
    """
    CANAL_CHOICES = [
        ('WEB', 'Web'),
        ('PUSH', 'Push Móvil'),
    ]

    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('ENVIANDO', 'Enviando'),
        ('ENVIADO', 'Enviado'),
        ('ERROR', 'Error'),
        ('REINTENTAR', 'Reintentar'),
    ]

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='usuario_id')
    canal = models.CharField(max_length=10, choices=CANAL_CHOICES)
    titulo = models.CharField(max_length=120)
    cuerpo = models.TextField()
    datos = models.JSONField(default=dict)
    estado = models.CharField(max_length=14, choices=ESTADO_CHOICES, default='PENDIENTE')
    reintentos = models.IntegerField(default=0)
    max_reintentos = models.IntegerField(default=3)
    proximo_intento = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cola_notificacion'
        managed = False
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['proximo_intento']),
        ]

    def __str__(self):
        return f"{self.canal} - {self.titulo} ({self.estado})"
