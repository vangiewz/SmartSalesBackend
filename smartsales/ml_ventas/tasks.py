from celery import shared_task
from .services import entrenar_modelo_ventas
from django.utils import timezone

@shared_task
def entrenar_modelo_ventas_periodico():
    print(f"[{timezone.now()}] Ejecutando entrenamiento automático...")
    try:
        result = entrenar_modelo_ventas()
        print(f"✅ Modelo entrenado correctamente: {result['modelo_path']}")
        return result
    except Exception as e:
        print(f"❌ Error al entrenar modelo: {e}")
        return {"error": str(e)}
