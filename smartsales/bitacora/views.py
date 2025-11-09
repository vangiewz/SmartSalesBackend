from rest_framework import generics, permissions, filters
from .models import Bitacora
from .serializers import BitacoraSerializer


class BitacoraListView(generics.ListAPIView):
    """
    Lista de registros de bitácora.
    CUALQUIER usuario puede acceder.
    """
    permission_classes = [permissions.AllowAny]
    queryset = Bitacora.objects.all()
    serializer_class = BitacoraSerializer

    # filtros básicos por querystring:
    # ?tabla=producto&operacion=UPDATE
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["fecha", "tabla", "operacion"]
    ordering = ["-fecha"]


class BitacoraDetailView(generics.RetrieveAPIView):
    """
    Detalle de un registro de bitácora por ID.
    También sin restricciones de permisos.
    """
    permission_classes = [permissions.AllowAny]
    queryset = Bitacora.objects.all()
    serializer_class = BitacoraSerializer
