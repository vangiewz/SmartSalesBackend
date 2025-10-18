from django.db import models

# Tablas mapeadas (unmanaged) en Supabase
class Usuario(models.Model):
    id = models.AutoField(primary_key=True)
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
    usuario = models.ForeignKey(Usuario, on_delete=models.DO_NOTHING, db_column="usuario_id")
    rol = models.ForeignKey(Rol, on_delete=models.DO_NOTHING, db_column="rol_id")

    class Meta:
        managed = False
        db_table = "rolesusuario"
        unique_together = (("usuario", "rol"),)
