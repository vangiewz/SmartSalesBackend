# smartsales/ai_reports/management/commands/train_ai_intents.py
from django.core.management.base import BaseCommand
from pathlib import Path
from joblib import dump

# scikit-learn
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report

# Dataset semilla: amplia con tus logs reales
TRAIN = [
    ("ventas por mes enero 2025", "ventas_por_mes"),
    ("mostrar ventas mensuales", "ventas_por_mes"),
    ("ventas por marca", "ventas_por_marca"),
    ("ventas por marca samsung", "ventas_por_marca"),
    ("reporte por marca", "ventas_por_marca"),
    ("ventas por categoria smartphone", "ventas_por_categoria"),
    ("ventas por categoría audio", "ventas_por_categoria"),
    ("top productos del trimestre", "top_productos"),
    ("productos más vendidos", "top_productos"),
    ("ventas por cliente juan", "ventas_por_cliente"),
    ("reporte por cliente", "ventas_por_cliente"),
    ("ticket promedio 2024", "ticket_promedio"),
    ("promedio de ticket", "ticket_promedio"),
    ("garantias por estado", "garantias_por_estado"),
    ("reporte de garantías", "garantias_por_estado"),
]

class Command(BaseCommand):
    help = "Entrena el clasificador de intenciones para ai_reports y guarda models/intent_clf.joblib"

    def handle(self, *args, **options):
        X = [t for t, _ in TRAIN]
        y = [l for _, l in TRAIN]

        pipe = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), analyzer="char_wb", lowercase=True)),
            ("clf", LogisticRegression(max_iter=1000))
        ])
        pipe.fit(X, y)

        y_pred = pipe.predict(X)
        self.stdout.write(self.style.SUCCESS("== Reporte en set de entrenamiento =="))
        self.stdout.write(classification_report(y, y_pred))

        out_dir = Path(__file__).resolve().parents[3] / "models"
        out_dir.mkdir(exist_ok=True)
        out_path = out_dir / "intent_clf.joblib"
        dump(pipe, out_path.as_posix())

        self.stdout.write(self.style.SUCCESS(f"Modelo guardado en: {out_path.as_posix()}"))
