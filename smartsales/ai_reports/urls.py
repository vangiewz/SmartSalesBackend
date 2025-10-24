from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import RunReportView, RunAudioReportView, PlantillaReporteViewSet

router = DefaultRouter()
router.register(r'plantillas', PlantillaReporteViewSet, basename='plantillas')

urlpatterns = [
    path('run', RunReportView.as_view(), name='ai_reports_run'),
    path('run-audio', RunAudioReportView.as_view(), name='ai_reports_run_audio'),
    path('', include(router.urls)),   # <-- aquí agregas el router
]