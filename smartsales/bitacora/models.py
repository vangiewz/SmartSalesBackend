from django.db import models


class Bitacora(models.Model):
    """
    Mapea la tabla audit_log de Postgres.
    Django NO crea ni modifica esta tabla (managed = False).
    """
    id = models.BigAutoField(primary_key=True)
    tabla = models.TextField()
    operacion = models.TextField()          # INSERT / UPDATE / DELETE / SNAPSHOT_INICIAL
    fecha = models.DateTimeField()
    usuario_id = models.UUIDField(null=True, blank=True)
    old_data = models.JSONField(null=True, blank=True)
    new_data = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "audit_log"
        managed = False          # muy importante
        ordering = ["-fecha"]

    def __str__(self):
        return f"[{self.fecha}] {self.tabla} {self.operacion}"
