from django.urls import path
from .views import (
    DescargarPlantillaView,
    ImportarCatalogoView,
    ExportarCatalogoView,
)

app_name = 'catalogo'

urlpatterns = [
    # Descargar plantilla para importar catálogo
    path(
        'descargar-plantilla/',
        DescargarPlantillaView.as_view(),
        name='descargar_plantilla'
    ),
    
    # Importar catálogo desde Excel
    path(
        'importar/',
        ImportarCatalogoView.as_view(),
        name='importar_catalogo'
    ),
    
    # Exportar catálogo a Excel
    path(
        'exportar/',
        ExportarCatalogoView.as_view(),
        name='exportar_catalogo'
    ),
]
