from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .serializers import RunReportSerializer, RunAudioSerializer
from .services.nlu import detect_intent
from .services.runner import run_sql
import io, pandas as pd

class RunReportView(APIView):
    permission_classes = [permissions.AllowAny]  # cámbialo luego a IsAnalyst/IsAdmin

    def post(self, request):
        ser = RunReportSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        prompt  = ser.validated_data['prompt']
        formato = ser.validated_data['formato']

        parsed = detect_intent(prompt)
        # print("NLU:", parsed)  # debug

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

        return Response({'detail':'Formato no soportado'}, status=400)

class RunAudioReportView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = RunAudioSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response({'detail':'Transcripción de audio no implementada aún.'}, status=501)
