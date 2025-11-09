# smartsales/carrito_voz/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from .serializers import (
    CarritoVozRequestSerializer,
    CarritoVozResponseSerializer,
)
from .services import interpretar_texto_carrito

# 👇 aquí están realmente tus modelos
from smartsales.ventas_historicas.models import Producto
from smartsales.listadoproductos.serializers import ProductoCatalogoSerializer


class ArmarCarritoVozAPIView(APIView):
    """
    UC-11 – Armar carrito por voz — Web / Móvil
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = CarritoVozRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        usuario_id = data["usuario_id"]
        texto = data["texto"]
        limite_items = data.get("limite_items", 10)

        resultado = interpretar_texto_carrito(
            usuario_id=usuario_id,
            texto=texto,
            limite_items=limite_items,
        )

        response_serializer = CarritoVozResponseSerializer(resultado)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class ProductosCarritoAPIView(APIView):
    """
    Devuelve el detalle de los productos que están en el carrito,
    a partir de una lista de IDs.

      GET /api/carrito-voz/productos-carrito/?ids=8,14,29
    """

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        ids_param = request.query_params.get("ids")
        if not ids_param:
            return Response(
                {"detail": "El parámetro 'ids' es requerido (ej: ids=8,14,29)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ids = [
                int(x.strip())
                for x in ids_param.split(",")
                if x.strip()
            ]
        except ValueError:
            return Response(
                {
                    "detail": (
                        "El parámetro 'ids' debe contener solo números "
                        "separados por comas."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not ids:
            return Response([], status=status.HTTP_200_OK)

        productos_qs = Producto.objects.filter(id__in=ids)

        # Mantener el orden según la lista de ids
        productos = sorted(
            productos_qs,
            key=lambda p: ids.index(p.id) if p.id in ids else 999999,
        )

        serializer = ProductoCatalogoSerializer(
            productos,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
