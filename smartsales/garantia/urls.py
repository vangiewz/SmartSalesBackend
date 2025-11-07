# smartsales/garantia/urls.py
from django.urls import path
from .views import ClaimListCreateView, ClaimEvaluateView, ClaimDetailView
from .ventas_elegibles import ventas_elegibles_garantia

urlpatterns = [
    # GET /api/garantia/ventas-elegibles/ - Lista de ventas con productos elegibles
    path("ventas-elegibles/", ventas_elegibles_garantia, name="ventas_elegibles"),
    
    # GET /api/garantia/mis/ - Listar garantías propias
    # POST /api/garantia/crear/ - Crear reclamo
    path("mis/", ClaimListCreateView.as_view(), name="mis_garantias"),
    path("crear/", ClaimListCreateView.as_view(), name="crear_garantia"),
    
    # GET /api/garantia/gestionar/ - Listar todas las garantías (técnico/admin)
    path("gestionar/", ClaimListCreateView.as_view(), name="gestionar_garantias"),
    
    # GET /api/garantia/detalle/{venta_id}/{producto_id}/{garantia_id}/
    path("detalle/<int:venta_id>/<int:producto_id>/<int:garantia_id>/",
         ClaimDetailView.as_view(), name="detalle_garantia"),
    
    # POST /api/garantia/evaluar/{garantia_id}/ - Ruta simplificada
    path("evaluar/<int:garantia_id>/",
         ClaimEvaluateView.as_view(), name="evaluar_garantia"),
    
    # Mantener endpoints originales para compatibilidad
    path("claims/", ClaimListCreateView.as_view(), name="claims_list_create"),
    path("claims/<int:venta_id>/<int:producto_id>/<int:garantia_id>/evaluate/",
         ClaimEvaluateView.as_view(), name="claim_evaluate"),
]
