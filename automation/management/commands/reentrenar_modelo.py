# automation/management/commands/reentrenar_modelo.py
from django.core.management.base import BaseCommand
from smartsales.ml_ventas.services import entrenar_modelo_ventas  # 👈 OJO acá

class Command(BaseCommand):
    help = "Entrena automáticamente el modelo de ventas"

    def handle(self, *args, **options):
        print("Entrenando modelo automáticamente...")
        result = entrenar_modelo_ventas()
        print("✅ Entrenado correctamente:", result["modelo_path"])
