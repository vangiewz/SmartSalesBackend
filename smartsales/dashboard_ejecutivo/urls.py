from django.urls import path
from .views import DashboardEjecutivoView

app_name = 'dashboard_ejecutivo'

urlpatterns = [
    # Dashboard ejecutivo principal
    path(
        '',
        DashboardEjecutivoView.as_view(),
        name='dashboard'
    ),
]
