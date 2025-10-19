from django.db import models

class Usuario(models.Model):
    id = models.UUIDField(primary_key=True)  # UUID de Supabase Auth
    nombre = models.CharField(max_length=120)
    telefono = models.CharField(max_length=40, null=True, blank=True)
    correo = models.CharField(max_length=180)

    class Meta:
        managed = False
        db_table = "usuario"

class Rol(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=80)

    class Meta:
        managed = False
        db_table = "roles"

class RolesUsuario(models.Model):
    usuario_id = models.UUIDField()
    rol_id = models.IntegerField()

    class Meta:
        managed = False
        db_table = "rolesusuario"
        unique_together = (("usuario_id", "rol_id"),)
