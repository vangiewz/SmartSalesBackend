from rest_framework import serializers
from .models import PlantillaReporte

class RunReportSerializer(serializers.Serializer):
    prompt  = serializers.CharField()
    formato = serializers.ChoiceField(choices=['json','csv','xlsx'], default='json')

class RunAudioSerializer(serializers.Serializer):
    audio   = serializers.FileField()
    formato = serializers.ChoiceField(choices=['json','csv','xlsx'], default='json')

class PlantillaReporteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlantillaReporte
        fields = '__all__'
        read_only_fields = ['usuario', 'usuario_id', 'creado_en', 'actualizado_en']