# smartsales/ml_ventas/services.py
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List

from django.conf import settings
from django.db import connection
from django.utils import timezone

import pandas as pd
from math import sqrt
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import joblib

# Campos que usaremos siempre que devolvamos la config
CONFIG_FIELDS: List[str] = [
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


def _row_to_config(row) -> Dict[str, Any]:
    return dict(zip(CONFIG_FIELDS, row))


# ---------------------------------------------------------
# CONFIGURACIÓN DEL MODELO (GET / PATCH)
# ---------------------------------------------------------
def get_model_config() -> Dict[str, Any]:
    """
    Devuelve la última configuración de ml_config_prediccion.
    Si no existe, crea una fila por defecto.
    """
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT id,
                   nombre_modelo,
                   horizonte_meses,
                   n_estimators,
                   max_depth,
                   min_samples_split,
                   min_samples_leaf,
                   incluir_categoria,
                   incluir_cliente,
                   actualizado_en,
                   actualizado_por
            FROM ml_config_prediccion
            ORDER BY actualizado_en DESC, id ASC
            LIMIT 1
            """
        )
        row = cur.fetchone()

        if row is None:
            # Crear config por defecto
            cur.execute(
                """
                INSERT INTO ml_config_prediccion
                  (nombre_modelo, horizonte_meses, n_estimators,
                   max_depth, min_samples_split, min_samples_leaf,
                   incluir_categoria, incluir_cliente, actualizado_en)
                VALUES
                  ('random_forest', 3, 100,
                   NULL, 2, 1,
                   TRUE, FALSE, NOW())
                RETURNING id,
                          nombre_modelo,
                          horizonte_meses,
                          n_estimators,
                          max_depth,
                          min_samples_split,
                          min_samples_leaf,
                          incluir_categoria,
                          incluir_cliente,
                          actualizado_en,
                          actualizado_por
                """
            )
            row = cur.fetchone()

    return _row_to_config(row)


def update_model_config(payload: Dict[str, Any], user_id=None) -> Dict[str, Any]:
    """
    Actualiza la configuración existente con los campos enviados.
    Solo se actualizan los campos presentes en payload.
    """
    current = get_model_config()

    allowed_keys = {
        "horizonte_meses",
        "n_estimators",
        "max_depth",
        "min_samples_split",
        "min_samples_leaf",
        "incluir_categoria",
        "incluir_cliente",
    }

    updates = {k: payload[k] for k in allowed_keys if k in payload}

    if not updates:
        # Nada que actualizar, devolvemos la config actual
        return current

    set_clauses = []
    values: List[Any] = []

    for key, value in updates.items():
        set_clauses.append(f"{key} = %s")
        values.append(value)

    set_sql = ", ".join(set_clauses)

    values.append(timezone.now())   # actualizado_en
    values.append(user_id)          # actualizado_por
    values.append(current["id"])    # WHERE id = ?

    with connection.cursor() as cur:
        cur.execute(
            f"""
            UPDATE ml_config_prediccion
               SET {set_sql},
                   actualizado_en = %s,
                   actualizado_por = %s
             WHERE id = %s
         RETURNING id,
                   nombre_modelo,
                   horizonte_meses,
                   n_estimators,
                   max_depth,
                   min_samples_split,
                   min_samples_leaf,
                   incluir_categoria,
                   incluir_cliente,
                   actualizado_en,
                   actualizado_por
            """,
            values,
        )
        row = cur.fetchone()

    return _row_to_config(row)


# ---------------------------------------------------------
# CARGA DE DATOS DE VENTAS
# ---------------------------------------------------------
def load_ventas_dataframe() -> pd.DataFrame:
    """
    Construye un DataFrame agregando ventas por mes:
      - periodo (primer día del mes)
      - año, mes
      - cantidad total
      - total en Bs
    Usa tablas: venta, detalleventa, producto
    """
    sql = """
    SELECT
      date_trunc('month', v.hora)     AS periodo,
      EXTRACT(YEAR  FROM v.hora)::int AS anio,
      EXTRACT(MONTH FROM v.hora)::int AS mes,
      SUM(dv.cantidad)                AS cantidad,
      SUM(dv.cantidad * p.precio)     AS total
    FROM venta v
    JOIN detalleventa dv ON dv.venta_id   = v.id
    JOIN producto      p ON p.id          = dv.producto_id
    GROUP BY 1,2,3
    ORDER BY periodo;
    """

    # Ojo: usar directamente `connection`, no `cursor.connection`
    df = pd.read_sql_query(sql, connection)
    return df


# ---------------------------------------------------------
# ENTRENAMIENTO DEL MODELO
# ---------------------------------------------------------
def entrenar_modelo_ventas() -> Dict[str, Any]:
    config = get_model_config()
    df = load_ventas_dataframe()

    if df.empty or len(df) < 10:
        raise ValueError("Se requieren al menos 10 filas de datos para entrenar el modelo.")

    # Orden cronológico y feature simple de tiempo
    df = df.sort_values("periodo").reset_index(drop=True)
    df["t"] = df.index + 1  # 1,2,3,... para representar el paso de tiempo

    target_col = "total"
    feature_cols = ["t", "mes", "anio"]

    X = df[feature_cols]
    y = df[target_col]

    # Split temporal (sin shuffle)
    test_size = 0.2 if len(df) >= 20 else 0.25
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, shuffle=False
    )

    model = RandomForestRegressor(
        n_estimators=config["n_estimators"],
        max_depth=config["max_depth"],
        min_samples_split=config["min_samples_split"],
        min_samples_leaf=config["min_samples_leaf"],
        random_state=42,
    )

    model.fit(X_train, y_train)

    # Por si el dataset es muy pequeño y el split deja test vacío
    if len(X_test) == 0:
        y_true = y_train
        y_pred = model.predict(X_train)
    else:
        y_true = y_test
        y_pred = model.predict(X_test)

    metric_r2 = float(r2_score(y_true, y_pred))
    metric_mae = float(mean_absolute_error(y_true, y_pred))
    metric_rmse = float(sqrt(mean_squared_error(y_true, y_pred)))

    # Carpeta donde guardamos el modelo
    base_dir = getattr(settings, "ML_MODELS_DIR", None)
    if not base_dir:
        # si no definiste ML_MODELS_DIR, usamos MEDIA_ROOT/ml_models
        root = getattr(settings, "MEDIA_ROOT", None)
        if root:
            base_dir = Path(root) / "ml_models"
        else:
            base_dir = Path(settings.BASE_DIR) / "ml_models"

    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    modelo_filename = "modelo_ventas_rf.pkl"
    modelo_path = base_dir / modelo_filename

    joblib.dump(
        {
            "model": model,
            "feature_cols": feature_cols,
            "target_col": target_col,
            "config": config,
        },
        modelo_path,
    )

    now = timezone.now()

    return {
        "status": "ok",
        "modelo": config["nombre_modelo"],
        "entrenado_en": now.isoformat(),
        "horizonte_meses": config["horizonte_meses"],
        "n_estimators": config["n_estimators"],
        "max_depth": config["max_depth"],
        "min_samples_split": config["min_samples_split"],
        "min_samples_leaf": config["min_samples_leaf"],
        "incluir_categoria": config["incluir_categoria"],
        "incluir_cliente": config["incluir_cliente"],
        "metric_r2": metric_r2,
        "metric_mae": metric_mae,
        "metric_rmse": metric_rmse,
        "filas_totales": int(len(df)),
        "filas_entrenamiento": int(len(X_train)),
        "filas_prueba": int(len(y_true)),
        "modelo_path": str(modelo_path),
        "feature_cols": feature_cols,
    }
