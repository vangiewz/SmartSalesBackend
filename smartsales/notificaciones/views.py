"""
Views para el sistema de notificaciones
"""
import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import SuscripcionMovil, ColaNotificacion
from .serializers import (
    SuscripcionMovilSerializer,
    ColaNotificacionSerializer,
    ActualizarTokenSerializer
)

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def actualizar_token_dispositivo(request):
    """
    Actualiza o crea el token de dispositivo móvil para el usuario autenticado
    Se debe llamar cada vez que el usuario inicie sesión exitosamente en móvil
    """
    try:
        serializer = ActualizarTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Token de dispositivo inválido', 'detalles': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        token_dispositivo = serializer.validated_data['token_dispositivo']
        usuario_id = request.user.id
        
        # Buscar suscripción existente para este usuario
        suscripcion, created = SuscripcionMovil.objects.update_or_create(
            usuario_id=usuario_id,
            defaults={
                'token_dispositivo': token_dispositivo,
                'activo': True,
                'actualizado_en': timezone.now()
            }
        )
        
        if created:
            logger.info(f"Nueva suscripción móvil creada para usuario {usuario_id}")
            mensaje = "Suscripción móvil creada exitosamente"
        else:
            logger.info(f"Token actualizado para usuario {usuario_id}")
            mensaje = "Token de dispositivo actualizado exitosamente"
        
        return Response(
            {
                'mensaje': mensaje,
                'suscripcion': SuscripcionMovilSerializer(suscripcion).data
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Error al actualizar token de dispositivo: {e}")
        return Response(
            {'error': 'Error al actualizar token de dispositivo'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_notificaciones_usuario(request):
    """
    Lista todas las notificaciones del usuario autenticado
    Opcionalmente filtrar por estado y canal
    """
    try:
        usuario_id = request.user.id
        
        # Filtros opcionales
        estado = request.query_params.get('estado', None)
        canal = request.query_params.get('canal', None)
        
        # Query base
        queryset = ColaNotificacion.objects.filter(usuario_id=usuario_id)
        
        # Aplicar filtros
        if estado:
            queryset = queryset.filter(estado=estado.upper())
        if canal:
            queryset = queryset.filter(canal=canal.upper())
        
        # Ordenar por más recientes
        notificaciones = queryset.order_by('-creado_en')[:50]  # Últimas 50
        
        serializer = ColaNotificacionSerializer(notificaciones, many=True)
        
        return Response(
            {
                'notificaciones': serializer.data,
                'total': queryset.count()
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Error al listar notificaciones: {e}")
        return Response(
            {'error': 'Error al obtener notificaciones'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_estado_suscripcion(request):
    """
    Obtiene el estado de la suscripción móvil del usuario autenticado
    """
    try:
        usuario_id = request.user.id
        
        suscripcion = SuscripcionMovil.objects.filter(
            usuario_id=usuario_id
        ).first()
        
        if not suscripcion:
            return Response(
                {
                    'suscrito': False,
                    'mensaje': 'No tienes una suscripción móvil activa'
                },
                status=status.HTTP_200_OK
            )
        
        return Response(
            {
                'suscrito': suscripcion.activo,
                'suscripcion': SuscripcionMovilSerializer(suscripcion).data
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Error al obtener estado de suscripción: {e}")
        return Response(
            {'error': 'Error al obtener estado de suscripción'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def desactivar_suscripcion(request):
    """
    Desactiva la suscripción móvil del usuario autenticado
    """
    try:
        usuario_id = request.user.id
        
        suscripcion = SuscripcionMovil.objects.filter(
            usuario_id=usuario_id
        ).first()
        
        if not suscripcion:
            return Response(
                {'mensaje': 'No tienes una suscripción móvil activa'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        suscripcion.activo = False
        suscripcion.save(update_fields=['activo', 'actualizado_en'])
        
        logger.info(f"Suscripción desactivada para usuario {usuario_id}")
        
        return Response(
            {'mensaje': 'Suscripción desactivada exitosamente'},
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Error al desactivar suscripción: {e}")
        return Response(
            {'error': 'Error al desactivar suscripción'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
