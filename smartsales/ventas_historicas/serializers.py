from rest_framework import serializers


class HistoricoQuerySerializer(serializers.Serializer):
    GROUP_BY_CHOICES = ("periodo", "producto", "cliente")
    GRANULARITY_CHOICES = ("day", "week", "month", "quarter", "year")

    group_by = serializers.ChoiceField(choices=GROUP_BY_CHOICES)
    granularity = serializers.ChoiceField(choices=GRANULARITY_CHOICES, required=False, default="month")

    # Fechas opcionales. Si no se envían, se usan MIN/MAX de la tabla venta.
    date_from = serializers.DateField(required=False, allow_null=True)
    date_to = serializers.DateField(required=False, allow_null=True)

    # Paginación opcional para producto/cliente. Si no se envía -> sin límite.
    limit = serializers.IntegerField(required=False, min_value=1, max_value=100000)
    offset = serializers.IntegerField(required=False, min_value=0, default=0)