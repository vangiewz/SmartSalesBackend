from django.urls import path
from .views import GestionDireccionesView

urlpatterns = [
    path("", GestionDireccionesView.as_view(), name="direcciones-list-create"),
    path("<int:id>/", GestionDireccionesView.as_view(), name="direcciones-detail"),
]
