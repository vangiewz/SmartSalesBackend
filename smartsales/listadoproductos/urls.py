from django.urls import path
from .views import ListadoProductosView, FiltrosDisponiblesView

urlpatterns = [
    path("", ListadoProductosView.as_view(), name="listado-productos"),
    path("filtros/", FiltrosDisponiblesView.as_view(), name="filtros-disponibles"),
]
