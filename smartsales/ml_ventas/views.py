# smartsales/ml_ventas/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import logging

from . import services

logger = logging.getLogger(__name__)


class ModeloPrediccionConfigView(APIView):
    """
    GET  /api/ml/config/  -> devuelve configuración actual
    PATCH /api/ml/config/ -> actualiza parámetros del modelo
    """

    def get(self, request, *args, **kwargs):
        config = services.get_model_config()
        return Response(config)

    def patch(self, request, *args, **kwargs):
        user_id = getattr(request.user, "id", None)
        config = services.update_model_config(request.data, user_id=user_id)
        return Response(config)


class TrainModeloView(APIView):
    """
    POST /api/ml/train/ -> entrena el modelo usando ventas históricas
    """

    def post(self, request, *args, **kwargs):
        try:
            result = services.entrenar_modelo_ventas()
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            # Errores esperados (p.ej. pocos datos)
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Error entrenando modelo de IA")
            return Response(
                {"detail": f"Error interno al entrenar el modelo de IA: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
