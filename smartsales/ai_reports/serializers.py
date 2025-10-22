from rest_framework import serializers

class RunReportSerializer(serializers.Serializer):
    prompt  = serializers.CharField()
    formato = serializers.ChoiceField(choices=['json','csv','xlsx'], default='json')

class RunAudioSerializer(serializers.Serializer):
    audio   = serializers.FileField()
    formato = serializers.ChoiceField(choices=['json','csv','xlsx'], default='json')
