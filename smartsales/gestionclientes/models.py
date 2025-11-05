import uuid
from django.db import models

"""
Modelos mapeados a tablas existentes en la BD (managed = False).
Se añade is_active para implementar soft-delete.
"""

class Usuario(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=120)
    telefono = models.CharField(max_length=40, null=True, blank=True)
    correo = models.EmailField(max_length=180, null=True, blank=True)
    is_active = models.BooleanField(default=True)  # soft-delete flag (mirar SQL para crear la columna)

    class Meta:
        db_table = "usuario"
        managed = False

    def __str__(self):
        return f"{self.nombre} ({self.correo})"


class UsuarioRol(models.Model):
    id = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, db_column="usuario_id", to_field="id", on_delete=models.CASCADE, related_name="roles")
    rol_id = models.IntegerField()
    role = models.CharField(max_length=120, null=True, blank=True)

    class Meta:
        db_table = "rolesusuario"
        managed = False

    def __str__(self):
        return f"{self.usuario_id} -> {self.rol_id}"