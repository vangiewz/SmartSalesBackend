from rest_framework import serializers


class BuscarClienteSerializer(serializers.Serializer):
    """Serializer para buscar cliente por correo electrónico"""
    correo = serializers.EmailField(required=True)


class ClienteEncontradoSerializer(serializers.Serializer):
    """Serializer para mostrar datos del cliente encontrado"""
    usuario_id = serializers.UUIDField()
    nombre = serializers.CharField()
    correo = serializers.EmailField()
    telefono = serializers.CharField(allow_null=True, allow_blank=True)


class ProductoVentaManualSerializer(serializers.Serializer):
    """Serializer para un producto en la venta manual"""
    producto_id = serializers.IntegerField(min_value=1)
    nombre = serializers.CharField(read_only=True)
    precio = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    cantidad = serializers.IntegerField(min_value=1)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)


class RegistrarVentaManualSerializer(serializers.Serializer):
    """
    Serializer para registrar una venta manual en mostrador.
    El vendedor selecciona cliente y productos manualmente.
    """
    cliente_correo = serializers.EmailField(
        required=True,
        help_text="Correo electrónico del cliente que realiza la compra"
    )
    
    productos = serializers.ListField(
        child=ProductoVentaManualSerializer(),
        min_length=1,
        help_text="Lista de productos con sus cantidades"
    )
    
    direccion = serializers.CharField(
        required=True,
        max_length=500,
        help_text="Dirección de entrega o 'Retiro en tienda'"
    )
    
    metodo_pago = serializers.ChoiceField(
        choices=['efectivo', 'tarjeta', 'transferencia'],
        default='efectivo',
        help_text="Método de pago utilizado en mostrador"
    )


class ResumenVentaManualSerializer(serializers.Serializer):
    """Serializer para mostrar el resumen de la venta manual registrada"""
    venta_id = serializers.IntegerField()
    cliente_nombre = serializers.CharField()
    cliente_correo = serializers.EmailField()
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    direccion = serializers.CharField()
    metodo_pago = serializers.CharField()
    fecha = serializers.DateTimeField()
    productos = serializers.ListField(child=ProductoVentaManualSerializer())
    vendedor_nombre = serializers.CharField()
    pago_id = serializers.IntegerField()


class BuscarProductoSerializer(serializers.Serializer):
    """Serializer para buscar productos por nombre o código"""
    busqueda = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
        help_text="Nombre o parte del nombre del producto a buscar (vacío = todos)"
    )


class ProductoDisponibleSerializer(serializers.Serializer):
    """Serializer para mostrar producto disponible con información completa"""
    producto_id = serializers.IntegerField()
    nombre = serializers.CharField()
    precio = serializers.DecimalField(max_digits=12, decimal_places=2)
    stock = serializers.IntegerField()
    marca = serializers.CharField()
    tipo = serializers.CharField()
    tiempo_garantia = serializers.IntegerField(help_text="Días de garantía")


class AgregarAlCarritoSerializer(serializers.Serializer):
    """Serializer para agregar un producto al carrito de venta manual"""
    producto_id = serializers.IntegerField(min_value=1, help_text="ID del producto a agregar")
    cantidad = serializers.IntegerField(min_value=1, help_text="Cantidad a agregar")


class ItemCarritoSerializer(serializers.Serializer):
    """Serializer para un item en el carrito"""
    producto_id = serializers.IntegerField()
    nombre = serializers.CharField()
    precio = serializers.DecimalField(max_digits=12, decimal_places=2)
    cantidad = serializers.IntegerField()
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)
    stock_disponible = serializers.IntegerField()
    marca = serializers.CharField()
    tipo = serializers.CharField()


class CarritoResponseSerializer(serializers.Serializer):
    """Serializer para respuesta del carrito"""
    items = serializers.ListField(child=ItemCarritoSerializer())
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    cantidad_items = serializers.IntegerField()


class ActualizarCantidadSerializer(serializers.Serializer):
    """Serializer para actualizar cantidad de un producto en el carrito"""
    producto_id = serializers.IntegerField(min_value=1)
    cantidad = serializers.IntegerField(min_value=1)
