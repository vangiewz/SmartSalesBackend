# backend/ml_ventas/models.py
from django.db import models


class ModeloPrediccionConfig(models.Model):
    """
    Mapea la tabla existente ml_config_prediccion.
    OJO: managed = False porque la tabla ya la creaste con SQL.
    """
    id = models.AutoField(primary_key=True)
    nombre_modelo = models.CharField(max_length=80, unique=True)
    horizonte_meses = models.IntegerField()
    n_estimators = models.IntegerField()
    max_depth = models.IntegerField(null=True, blank=True)
    min_samples_split = models.IntegerField()
    min_samples_leaf = models.IntegerField()
    incluir_categoria = models.BooleanField()
    incluir_cliente = models.BooleanField()
    actualizado_en = models.DateTimeField()
    actualizado_por = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "ml_config_prediccion"
        managed = False  # no crear/alterar tabla con migrations

    def __str__(self) -> str:
        return f"Config {self.nombre_modelo}"
