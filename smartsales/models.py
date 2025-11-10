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


class Venta(models.Model):
    id = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='usuario_id')
    total = models.DecimalField(max_digits=12, decimal_places=2)
    hora = models.DateTimeField(auto_now_add=True)
    direccion = models.TextField()

    class Meta:
        managed = False
        db_table = "venta"


class Producto(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=160)
    precio = models.DecimalField(max_digits=12, decimal_places=2)
    tiempogarantia = models.IntegerField()  # días
    stock = models.IntegerField()
    marca_id = models.IntegerField()
    tipoproducto_id = models.IntegerField()
    imagen_key = models.TextField(null=True, blank=True)
    id_vendedor = models.UUIDField()

    class Meta:
        managed = False
        db_table = "producto"


class EstadoGarantia(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=60, unique=True)

    class Meta:
        managed = False
        db_table = "estadogarantia"


class Garantia(models.Model):
    id = models.IntegerField(primary_key=True)
    venta_id = models.IntegerField()
    producto_id = models.IntegerField()
    motivo = models.CharField(max_length=200)
    cantidad = models.IntegerField()
    hora = models.DateTimeField(auto_now_add=True)
    reemplazo = models.BooleanField(null=True, blank=True)
    estadogarantia_id = models.IntegerField()

    class Meta:
        managed = False
        db_table = "garantia"
