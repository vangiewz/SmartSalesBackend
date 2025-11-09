# smartsales/carrito_voz/urls.py

from django.urls import path
from .views import ArmarCarritoVozAPIView, ProductosCarritoAPIView

app_name = "carrito_voz"

urlpatterns = [
    # POST /api/carrito-voz/carrito-voz/
    path(
        "carrito-voz/",
        ArmarCarritoVozAPIView.as_view(),
        name="carrito-voz",
    ),

    # GET /api/carrito-voz/productos-carrito/?ids=8,14,29
    path(
        "productos-carrito/",
        ProductosCarritoAPIView.as_view(),
        name="productos-carrito",
    ),
]
