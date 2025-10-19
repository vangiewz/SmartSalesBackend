from pathlib import Path
import os
from datetime import timedelta
from dotenv import load_dotenv
import dj_database_url

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-NO-USAR-EN-PROD")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS_ENV = os.getenv("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "[::1]",
] + ([h.strip() for h in ALLOWED_HOSTS_ENV.split(",") if h.strip()] if ALLOWED_HOSTS_ENV else [])

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    # sin admin
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "corsheaders",
    "rest_framework",
    "smartsales",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

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

# =========================
# Database (Transaction Pooler 6543)
# =========================
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Falta DATABASE_URL en .env")

DB_SSL_REQUIRE = os.getenv("DB_SSL_REQUIRE", "True").lower() == "true"

DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=0,              # TX pooler: conexiones cortas por request
        ssl_require=DB_SSL_REQUIRE,
    )
}

# Recomendado con TX pooler
DISABLE_SERVER_SIDE_CURSORS = True

# Opciones de conexión (TLS + timeouts + keepalives)
DATABASES["default"].setdefault("OPTIONS", {})
DATABASES["default"]["OPTIONS"].update({
    "sslmode": "require",
    "keepalives": 1,
    "keepalives_idle": 30,
    "keepalives_interval": 10,
    "keepalives_count": 5,
    "options": "-c statement_timeout=30000",
})

# =========================
# Passwords / i18n / estáticos
# =========================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es"
TIME_ZONE = "America/La_Paz"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =========================
# DRF / JWT
# =========================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

ACCESS_MIN = int(os.getenv("JWT_ACCESS_MINUTES", "60"))
REFRESH_D = int(os.getenv("JWT_REFRESH_DAYS", "7"))
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=ACCESS_MIN),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=REFRESH_D),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# =========================
# CORS / CSRF
# =========================
CORS_ALLOW_ALL_ORIGINS = os.getenv("CORS_ALLOW_ALL_ORIGINS", "True").lower() == "true"
FRONTEND_ORIGINS = [o.strip() for o in os.getenv("FRONTEND_ORIGINS", "").split(",") if o.strip()]
if FRONTEND_ORIGINS:
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = FRONTEND_ORIGINS

CSRF_TRUSTED = [o.strip() for o in os.getenv("CSRF_TRUSTED", "").split(",") if o.strip()]
if CSRF_TRUSTED:
    CSRF_TRUSTED_ORIGINS = CSRF_TRUSTED

# =========================
# Logging (para ver el traceback del 500)
# =========================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "django.request": {      # errores de vistas (500)
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.db.backends": {  # warnings/errores de DB (útil para pooler)
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
}