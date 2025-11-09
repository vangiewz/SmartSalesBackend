from django.urls import path
from .views import BitacoraListView, BitacoraDetailView

urlpatterns = [
    # GET /api/bitacora/ - listar todos los registros
    path("", BitacoraListView.as_view(), name="bitacora_list"),

    # GET /api/bitacora/<id>/ - detalle de un registro
    path("<int:pk>/", BitacoraDetailView.as_view(), name="bitacora_detail"),
]
