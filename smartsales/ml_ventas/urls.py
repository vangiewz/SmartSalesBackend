# backend/ml_ventas/urls.py
from django.urls import path
from .views import ModeloPrediccionConfigView

urlpatterns = [
    path("config/", ModeloPrediccionConfigView.as_view(), name="ml-model-config"),
]
