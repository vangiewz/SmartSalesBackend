# smartsales/ml_ventas/urls.py
from django.urls import path
from .views import ModeloPrediccionConfigView, TrainModeloView

urlpatterns = [
    path("config/", ModeloPrediccionConfigView.as_view(), name="ml-model-config"),
    path("train/",  TrainModeloView.as_view(),            name="ml-model-train"),
]
