"""
Django settings for core project.

Optimizado para despliegue en Render.
"""

from pathlib import Path
import os
import environ
import dj_database_url  # 👈 para conectar DB con DATABASE_URL

# ====== Paths ======
BASE_DIR = Path(__file__).resolve().parent.parent

# ====== Environment ======
env = environ.Env(
    DEBUG=(bool, False)
)
# Leer variables desde archivo .env en local
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# ====== Seguridad ======
SECRET_KEY = env("SECRET_KEY")  # ⚠️ definido en .env o en Render
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", ".onrender.com", ".ngrok-free.dev",])

# ====== Aplicaciones ======
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    # ====== tu app ======
    "smartsales",  # 👈 /auth/register, /auth/login, /auth/me
    "smartsales.ai_reports",
    "smartsales.gestionclientes",
    "smartsales.ventas_historicas",
    "smartsales.ml_ventas",
    "smartsales.notificaciones",  # 👈 Sistema de notificaciones
    "automation",
    "smartsales.bitacora",
    "django_extensions",
]

# ====== Middleware ======
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # 👈 CORS primero
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # 👈 servir archivos estáticos
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

# ====== Templates ======
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

# ====== Base de Datos ======
# 🔧 Optimizado para Supabase Transaction Pooler (free tier)
DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get("DATABASE_URL"),
        conn_max_age=0,  # 👈 NO reusar conexiones (pooler ya lo maneja)
        conn_health_checks=True,  # 👈 validar conexión antes de usar
    )
}

# 🔧 Configuraciones adicionales para el pooler de Supabase
DATABASES["default"]["OPTIONS"] = {
    "connect_timeout": 10,
    "options": "-c statement_timeout=30000",
    "keepalives": 1,
    "keepalives_idle": 10,
    "keepalives_interval": 5,
    "keepalives_count": 3,
    "sslmode": "require",
    # Forzar uso de IPv4 únicamente
    "hostaddr": None,  # dejar que resuelva el DNS
}

# Configuración adicional para evitar problemas de pool
DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True  # importante para pgBouncer/Pooler

# ====== Validaciones de Password ======
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ====== Internacionalización ======
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ====== Archivos estáticos ======
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ====== Primary Key por defecto ======
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ====== Logging ======
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',  # Solo errores de DB
            'propagate': False,
        },
        'smartsales': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ====== CORS ======
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",      # desarrollo local (Vite)
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5175",
    # 👇 tu dominio de Vercel para producción del frontend
    "https://smart-sales-frontend-c82v.vercel.app",
]
# 👉 Si quieres permitir previews de Vercel (opcionales), descomenta:
CORS_ALLOWED_ORIGIN_REGEXES = [r"^https://.*\.vercel\.app$"]

CORS_ALLOW_HEADERS = [
    "authorization",
    "content-type",
    "x-requested-with",
    "x-platform",  # 👈 Header personalizado para modo móvil
]

CORS_ALLOW_METHODS = [
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
]

CORS_ALLOW_CREDENTIALS = False  # No usas cookies; solo tokens por header

# ====== DRF (auth Supabase) ======
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "smartsales.authsupabase.jwt.SupabaseJWTAuthentication",  # 👈 usa el JWT de Supabase (HS256)
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}

ML_MODELS_DIR = BASE_DIR / "ml_models"

# ====== Notificaciones ======
# Firebase Cloud Messaging (para push notifications)
FIREBASE_CREDENTIALS_PATH = env("FIREBASE_CREDENTIALS_PATH", default=None)  # Ruta al archivo JSON de Firebase

# SendGrid (para notificaciones por email)
SENDGRID_API_KEY = env("SENDGRID_API_KEY", default=None)
SENDGRID_FROM_EMAIL = env("SENDGRID_FROM_EMAIL", default="notificaciones@smartsales.com")
