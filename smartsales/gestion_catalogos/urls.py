from django.urls import path
from .views import (
    # Tipos de Producto
    ListarTiposProductoView,
    CrearTipoProductoView,
    ActualizarTipoProductoView,
    EliminarTipoProductoView,
    # Marcas
    ListarMarcasView,
    CrearMarcaView,
    ActualizarMarcaView,
    EliminarMarcaView,
)

app_name = 'gestion_catalogos'

urlpatterns = [
    # ==================== TIPOS DE PRODUCTO ====================
    
    # Listar todos los tipos de producto
    path(
        'tipos-producto/',
        ListarTiposProductoView.as_view(),
        name='listar_tipos_producto'
    ),
    
    # Crear nuevo tipo de producto
    path(
        'tipos-producto/crear/',
        CrearTipoProductoView.as_view(),
        name='crear_tipo_producto'
    ),
    
    # Actualizar tipo de producto
    path(
        'tipos-producto/<int:tipo_id>/',
        ActualizarTipoProductoView.as_view(),
        name='actualizar_tipo_producto'
    ),
    
    # Eliminar tipo de producto
    path(
        'tipos-producto/<int:tipo_id>/eliminar/',
        EliminarTipoProductoView.as_view(),
        name='eliminar_tipo_producto'
    ),
    
    # ==================== MARCAS ====================
    
    # Listar todas las marcas
    path(
        'marcas/',
        ListarMarcasView.as_view(),
        name='listar_marcas'
    ),
    
    # Crear nueva marca
    path(
        'marcas/crear/',
        CrearMarcaView.as_view(),
        name='crear_marca'
    ),
    
    # Actualizar marca
    path(
        'marcas/<int:marca_id>/',
        ActualizarMarcaView.as_view(),
        name='actualizar_marca'
    ),
    
    # Eliminar marca
    path(
        'marcas/<int:marca_id>/eliminar/',
        EliminarMarcaView.as_view(),
        name='eliminar_marca'
    ),
]
