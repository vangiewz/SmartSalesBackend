from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, viewsets, exceptions
from django.utils import timezone

from .serializers import RunReportSerializer, RunAudioSerializer, PlantillaReporteSerializer
from .services.nlu import detect_intent
from .services.runner import run_sql
from .models import PlantillaReporte

import io
import pandas as pd


class RunReportView(APIView):
    permission_classes = [permissions.AllowAny]  # cámbialo luego a IsAnalyst/IsAdmin

    def post(self, request):
        ser = RunReportSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        prompt = ser.validated_data['prompt']
        formato = ser.validated_data['formato']

        parsed = detect_intent(prompt)
        result = run_sql(parsed['intent'], parsed['start'], parsed['end'], filters=parsed.get('filters'))

        if formato == 'json':
            return Response(result, status=status.HTTP_200_OK)

        df = pd.DataFrame(result['rows'])
        if formato == 'csv':
            buf = io.StringIO()
            df.to_csv(buf, index=False)
            data = buf.getvalue().encode('utf-8')
            return Response(data, content_type='text/csv')

        if formato == 'xlsx':
            out = io.BytesIO()
            with pd.ExcelWriter(out, engine='openpyxl') as xw:
                df.to_excel(xw, index=False, sheet_name='Reporte')
            return Response(out.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        return Response({'detail': 'Formato no soportado'}, status=400)


class RunAudioReportView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = RunAudioSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response({'detail': 'Transcripción de audio no implementada aún.'}, status=501)


class PlantillaReporteViewSet(viewsets.ModelViewSet):
    serializer_class = PlantillaReporteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _resolve_user_uuid(self):
        u = self.request.user
        for attr in ("id", "sub", "user_id", "uuid"):
            val = getattr(u, attr, None)
            if val:
                return str(val)
        raw = getattr(u, "raw", None) or getattr(u, "payload", None)
        if isinstance(raw, dict) and raw.get("sub"):
            return str(raw["sub"])
        auth = getattr(self.request, "auth", None)
        if isinstance(auth, dict) and auth.get("sub"):
            return str(auth["sub"])
        raise exceptions.PermissionDenied("No se pudo resolver el id del usuario desde request.user")

    def get_queryset(self):
        user_uuid = self._resolve_user_uuid()
        return PlantillaReporte.objects.filter(usuario_id=user_uuid)

    def perform_create(self, serializer):
        user_uuid = self._resolve_user_uuid()
        now = timezone.now()
        serializer.save(usuario_id=user_uuid, creado_en=now, actualizado_en=now)

    def perform_update(self, serializer):
        serializer.save(actualizado_en=timezone.now())