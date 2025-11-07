# smartsales/garantia/views.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from smartsales.garantia.serializers import (
    ClaimCreateSerializer, ClaimEvaluateSerializer, ClaimListQuerySerializer, ClaimResponseSerializer,
    ClaimDetailResponseSerializer
)
from smartsales.garantia import services, messages as MSG
from smartsales.rolesusuario.permissions import (
    IsTecnicoRole, IsTecnicoOrAdminRole, ROLE_TECNICO_NAME, ROLE_ADMIN_NAME, user_has_role
)

class ClaimListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        q = ClaimListQuerySerializer(data=request.query_params)
        q.is_valid(raise_exception=True)
        filtros = q.validated_data

        # Alcance: cliente => own; técnico/admin => global
        scope = "own"
        if user_has_role(request.user.id, ROLE_TECNICO_NAME) or user_has_role(request.user.id, ROLE_ADMIN_NAME):
            scope = "global"

        data = services.listar(request.user.id, scope, filtros)
        return Response({
            "count": data["count"],
            "page": filtros.get("page", 1),
            "page_size": filtros.get("page_size", 20),
            "results": data["results"],
        })

    def post(self, request):
        s = ClaimCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            payload = services.crear_reclamo(
                user_id=request.user.id,
                venta_id=s.validated_data["venta_id"],
                producto_id=s.validated_data["producto_id"],
                cantidad=s.validated_data["cantidad"],
                motivo=s.validated_data["motivo"],
            )
            return Response(ClaimResponseSerializer(payload).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)

class ClaimDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, venta_id: int, producto_id: int, garantia_id: int):
        try:
            # Verificar acceso: técnico/admin ven todo, cliente solo lo suyo
            scope = "own"
            if user_has_role(request.user.id, ROLE_TECNICO_NAME) or user_has_role(request.user.id, ROLE_ADMIN_NAME):
                scope = "global"
            
            payload = services.detalle_garantia(
                user_id=request.user.id,
                scope=scope,
                venta_id=venta_id,
                producto_id=producto_id,
                garantia_id=garantia_id
            )
            return Response(ClaimDetailResponseSerializer(payload).data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=404)

class ClaimEvaluateView(APIView):
    permission_classes = [IsAuthenticated, IsTecnicoRole]

    def post(self, request, garantia_id: int = None, venta_id: int = None, producto_id: int = None):
        """
        Evaluación de garantía. Soporta dos rutas:
        - POST /api/garantia/evaluar/{garantia_id}/ (simplificada)
        - PATCH /api/garantia/claims/{venta_id}/{producto_id}/{garantia_id}/evaluate/ (completa)
        """
        try:
            # Logs de debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"👤 Usuario: {request.user.id}")
            logger.info(f"📝 garantia_id={garantia_id}, venta_id={venta_id}, producto_id={producto_id}")
            
            # Verificar roles del usuario
            from smartsales.rolesusuario.permissions import user_has_role, ROLE_TECNICO_ID, ROLE_TECNICO_NAME
            has_tecnico_by_id = user_has_role(request.user.id, ROLE_TECNICO_ID)
            has_tecnico_by_name = user_has_role(request.user.id, ROLE_TECNICO_NAME)
            logger.info(f"👤 Tiene rol Técnico (por ID {ROLE_TECNICO_ID}): {has_tecnico_by_id}")
            logger.info(f"👤 Tiene rol Técnico (por nombre '{ROLE_TECNICO_NAME}'): {has_tecnico_by_name}")
            
            s = ClaimEvaluateSerializer(data=request.data)
            s.is_valid(raise_exception=True)
            logger.info(f"✅ Datos validados: {s.validated_data}")
            
            # Si viene garantia_id solo, buscar venta_id y producto_id
            if garantia_id and not (venta_id and producto_id):
                logger.info(f"🔍 Buscando venta_id y producto_id para garantia_id={garantia_id}")
                from smartsales.garantia.repository import get_garantia_simple
                garantia_data = get_garantia_simple(garantia_id)
                if not garantia_data:
                    logger.error(f"❌ No se encontró garantía con id={garantia_id}")
                    return Response({"detail": MSG.ERR_NOT_FOUND}, status=404)
                venta_id, producto_id = garantia_data
                logger.info(f"✅ Encontrado: venta_id={venta_id}, producto_id={producto_id}")
            
            # Convertir evaluacion a reemplazo si viene en ese formato
            reemplazo = s.validated_data.get("reemplazo", None)
            evaluacion = s.validated_data.get("evaluacion", None)
            
            if evaluacion:
                if evaluacion == "Reemplazar":
                    reemplazo = True
                elif evaluacion == "Reparar":
                    reemplazo = False
                elif evaluacion == "Rechazar":
                    reemplazo = None
            
            logger.info(f"📊 Evaluación: {evaluacion}, reemplazo: {reemplazo}")
            
            payload = services.evaluar_reclamo(
                tecnico_id=request.user.id,
                venta_id=venta_id,
                producto_id=producto_id,
                garantia_id=garantia_id,
                reemplazo=reemplazo
            )
            logger.info(f"✅ Evaluación exitosa")
            return Response(ClaimResponseSerializer(payload).data)
        except ValueError as e:
            logger.error(f"❌ ValueError: {str(e)}")
            msg = str(e)
            return Response({"detail": msg}, status=404 if msg == MSG.ERR_NOT_FOUND else 400)
        except Exception as e:
            logger.error(f"❌ Error inesperado: {str(e)}", exc_info=True)
            return Response({"detail": f"Error interno: {str(e)}"}, status=500)

    def patch(self, request, venta_id: int, producto_id: int, garantia_id: int):
        """Evaluación con ruta completa (compatibilidad)"""
        return self.post(request, garantia_id, venta_id, producto_id)


