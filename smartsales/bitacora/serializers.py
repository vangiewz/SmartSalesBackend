from rest_framework import serializers
from .models import Bitacora


class BitacoraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bitacora
        fields = "__all__"
