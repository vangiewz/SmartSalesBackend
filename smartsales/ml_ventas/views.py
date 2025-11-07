# backend/ml_ventas/views.py
from rest_framework import generics, permissions
from django.utils import timezone

from .models import ModeloPrediccionConfig
from .serializers import ModeloPrediccionConfigSerializer


class ModeloPrediccionConfigView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/ml/config/   -> obtiene la configuración actual
    PUT  /api/ml/config/   -> actualiza toda la config
    PATCH /api/ml/config/  -> actualiza parcialmente
    """
    serializer_class = ModeloPrediccionConfigSerializer
    permission_classes = [permissions.AllowAny]  # sin restricciones

    def get_object(self):
        """
        Garantiza que siempre exista una fila para 'random_forest'.
        Si está vacía la tabla, crea un registro por defecto.
        """
        obj = (
            ModeloPrediccionConfig.objects.filter(
                nombre_modelo__iexact="random_forest"
            ).first()
        )
        if obj is None:
            obj = ModeloPrediccionConfig.objects.create(
                nombre_modelo="random_forest",
                horizonte_meses=3,
                n_estimators=100,
                max_depth=None,
                min_samples_split=2,
                min_samples_leaf=1,
                incluir_categoria=True,
                incluir_cliente=False,
                actualizado_en=timezone.now(),
                actualizado_por=None,
            )
        return obj

    def perform_update(self, serializer):
        # actualiza también la fecha de actualización
        instance = serializer.save(actualizado_en=timezone.now())
        return instance
