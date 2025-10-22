from django.urls import path
from .views import RunReportView, RunAudioReportView

urlpatterns = [
    path('run', RunReportView.as_view(), name='ai_reports_run'),
    path('run-audio', RunAudioReportView.as_view(), name='ai_reports_run_audio'),
]
