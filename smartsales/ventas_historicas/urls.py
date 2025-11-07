from django.urls import path
from .views import HistoricoVentasView

app_name = "ventas_historicas"

urlpatterns = [
    # Ruta recomendada (quedará /api/ventas-historicas/historico/)
    path("historico/", HistoricoVentasView.as_view(), name="historico"),

    # Ruta legacy para que lo que ya tenías siga funcionando (doble api)
    path("api/historico/", HistoricoVentasView.as_view(), name="historico_legacy"),
]