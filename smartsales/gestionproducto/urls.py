from django.urls import path
from .views import (
    MarcaListView, TipoProductoListView,
    ProductoListCreateView, ProductoDetailView,
)

urlpatterns = [
    # catálogos
    path("marcas/", MarcaListView.as_view(), name="gp_marcas"),
    path("tipos/",  TipoProductoListView.as_view(), name="gp_tipos"),

    # productos
    path("",          ProductoListCreateView.as_view(), name="gp_list_create"),
    path("<int:pk>/", ProductoDetailView.as_view(),     name="gp_detail"),
]
