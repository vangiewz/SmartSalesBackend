from django.urls import path
from .views import (
    BuscarClienteView,
    BuscarProductoView,
    RegistrarVentaManualView,
    AgregarAlCarritoView,
    ObtenerCarritoView,
    ActualizarCantidadCarritoView,
    EliminarDelCarritoView,
    VaciarCarritoView,
)

app_name = 'venta_manual'

urlpatterns = [
    # Buscar cliente por correo electrónico
    path(
        'buscar-cliente/',
        BuscarClienteView.as_view(),
        name='buscar_cliente'
    ),
    
    # Buscar productos disponibles
    path(
        'buscar-producto/',
        BuscarProductoView.as_view(),
        name='buscar_producto'
    ),
    
    # Registrar venta manual en mostrador
    path(
        'registrar/',
        RegistrarVentaManualView.as_view(),
        name='registrar_venta'
    ),
    
    # === CARRITO DE VENTA MANUAL ===
    
    # Agregar producto al carrito
    path(
        'carrito/agregar/',
        AgregarAlCarritoView.as_view(),
        name='agregar_carrito'
    ),
    
    # Obtener carrito actual
    path(
        'carrito/',
        ObtenerCarritoView.as_view(),
        name='obtener_carrito'
    ),
    
    # Actualizar cantidad de producto en carrito
    path(
        'carrito/actualizar/',
        ActualizarCantidadCarritoView.as_view(),
        name='actualizar_carrito'
    ),
    
    # Eliminar producto del carrito
    path(
        'carrito/eliminar/<int:producto_id>/',
        EliminarDelCarritoView.as_view(),
        name='eliminar_carrito'
    ),
    
    # Vaciar carrito completo
    path(
        'carrito/vaciar/',
        VaciarCarritoView.as_view(),
        name='vaciar_carrito'
    ),
]
