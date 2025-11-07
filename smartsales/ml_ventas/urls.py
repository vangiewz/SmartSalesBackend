from django.urls import path
from .views import ModeloPrediccionConfigView, TrainModeloView, PrediccionesModeloView

urlpatterns = [
    path("config/", ModeloPrediccionConfigView.as_view(), name="ml_config"),
    path("train/", TrainModeloView.as_view(), name="ml_train"),
    path("predict/", PrediccionesModeloView.as_view(), name="ml_predict"),
]
