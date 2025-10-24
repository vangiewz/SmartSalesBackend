from django.db import models

class PlantillaReporte(models.Model):
    usuario = models.ForeignKey(
        'smartsales.Usuario', # <-- nombre correcto de la app/modelo
        on_delete=models.CASCADE,
        db_column='usuario_id'
    )
    nombre = models.CharField(max_length=120)
    prompt = models.TextField()
    formato = models.CharField(max_length=12, blank=True, null=True)
    filtros = models.JSONField(blank=True, null=True)
    creado_en = models.DateTimeField()
    actualizado_en = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "plantilla_reporte"