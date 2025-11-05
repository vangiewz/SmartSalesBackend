from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db import transaction
from django.db.utils import IntegrityError
from django.db.models import Exists, OuterRef
from django.apps import apps
import logging

from .models import Usuario, UsuarioRol
from .serializers import (
    ClienteListSerializer,
    ClienteCreateSerializer,
    ClienteUpdateSerializer,
)

logger = logging.getLogger(__name__)
CLIENT_ROLE_ID = 1  # ajustá si tu rol cliente tiene otro id

class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    authentication_classes = []
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == "create":
            return ClienteCreateSerializer
        if self.action in ("update", "partial_update"):
            return ClienteUpdateSerializer
        return ClienteListSerializer

    def get_queryset(self):
        # Filtramos solo usuarios activos (soft-delete)
        sub = UsuarioRol.objects.filter(usuario_id=OuterRef("id"), rol_id=CLIENT_ROLE_ID)
        qs = Usuario.objects.annotate(is_cliente=Exists(sub)).filter(is_cliente=True, is_active=True)
        nombre = self.request.query_params.get("nombre")
        correo = self.request.query_params.get("correo")
        if nombre:
            qs = qs.filter(nombre__icontains=nombre)
        if correo:
            qs = qs.filter(correo__icontains=correo)
        return qs.order_by("nombre")

    def _find_venta_model(self):
        # Buscar dinámicamente el modelo Venta si existe (evita import estático)
        for model in apps.get_models():
            if model.__name__.lower() == "venta":
                return model
        return None

    def destroy(self, request, *args, **kwargs):
        """
        Soft-delete: marcamos is_active = False en lugar de borrar la fila física.
        Si preferís mantener delete físico, hay opciones alternativas (ver abajo).
        """
        instance = self.get_object()

        # Si existen ventas relacionadas, evitamos borrar (aunque en soft-delete no sería necesario,
        # aun así verificamos para prevenir inconsistencias lógicas)
        Venta = self._find_venta_model()
        if Venta is not None:
            try:
                ventas_existen = Venta.objects.filter(usuario_id=instance.id).exists()
            except Exception:
                ventas_existen = Venta.objects.filter(usuario=instance).exists()
        else:
            ventas_existen = False

        # En soft-delete permitimos marcar inactivo incluso si tiene ventas,
        # pero si preferís bloquearlo en ese caso, descomenta el bloque siguiente:
        # if ventas_existen:
        #     return Response(
        #         {"detail": "No se puede eliminar el cliente: tiene ventas asociadas. Considerá marcarlo como inactivo en lugar de eliminarlo."},
        #         status=status.HTTP_409_CONFLICT,
        #     )

        try:
            with transaction.atomic():
                # marcar como inactivo
                instance.is_active = False
                instance.save(update_fields=["is_active"])
                # borrar roles si querés (opcional)
                UsuarioRol.objects.filter(usuario_id=instance.id).delete()
        except IntegrityError as exc:
            logger.exception("IntegrityError al marcar usuario inactivo %s: %s", instance.id, exc)
            return Response({"detail": "No se pudo actualizar el cliente por restricciones de integridad."}, status=status.HTTP_409_CONFLICT)
        except Exception as exc:
            logger.exception("Error interno al marcar usuario inactivo %s: %s", instance.id, exc)
            return Response({"detail": "Error interno al eliminar el cliente."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(status=status.HTTP_204_NO_CONTENT)