from django.db import models


class Usuario(models.Model):
    id = models.UUIDField(primary_key=True)
    nombre = models.CharField(max_length=120)
    telefono = models.CharField(max_length=40, null=True, blank=True)
    correo = models.CharField(max_length=180)

    class Meta:
        managed = False
        db_table = "usuario"


class Marca(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=120)

    class Meta:
        managed = False
        db_table = "marca"


class TipoProducto(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=120)

    class Meta:
        managed = False
        db_table = "tipoproducto"


class Producto(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=160)
    precio = models.DecimalField(max_digits=12, decimal_places=2)
    tiempogarantia = models.IntegerField()
    stock = models.IntegerField()
    marca = models.ForeignKey(Marca, on_delete=models.DO_NOTHING, db_column="marca_id")
    tipoproducto = models.ForeignKey(TipoProducto, on_delete=models.DO_NOTHING, db_column="tipoproducto_id")
    id_vendedor = models.UUIDField()
    imagen_key = models.TextField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "producto"


class Venta(models.Model):
    id = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.DO_NOTHING, db_column="usuario_id")
    total = models.DecimalField(max_digits=12, decimal_places=2)
    hora = models.DateTimeField()
    direccion = models.TextField()

    class Meta:
        managed = False
        db_table = "venta"