from django.urls import path
from .views import HistorialPagosView, DetallePagoView

urlpatterns = [
    path("", HistorialPagosView.as_view(), name="historial-pagos"),
    path("<int:pago_id>/", DetallePagoView.as_view(), name="detalle-pago"),
]
