# backend/ml_ventas/serializers.py
from rest_framework import serializers
from .models import ModeloPrediccionConfig


class ModeloPrediccionConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModeloPrediccionConfig
        fields = [
            "id",
            "nombre_modelo",
            "horizonte_meses",
            "n_estimators",
            "max_depth",
            "min_samples_split",
            "min_samples_leaf",
            "incluir_categoria",
            "incluir_cliente",
            "actualizado_en",
            "actualizado_por",
        ]
        # dejamos nombre_modelo y timestamps sólo lectura
        read_only_fields = ["id", "nombre_modelo", "actualizado_en", "actualizado_por"]
