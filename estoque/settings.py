"""
Django settings for the Estoque project.

Industrial kitchen inventory management system.
"""
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega variáveis de .env (se existir) para configurar o Django
# sem precisar expor segredos em variáveis de ambiente do sistema.
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass  # python-dotenv não instalado; usa apenas os.environ

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-CHAVE-DE-DESENVOLVIMENTO-TROQUE-EM-PRODUCAO-1234567890",
)
DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "yes")
ALLOWED_HOSTS = [h.strip() for h in os.environ.get(
    "ALLOWED_HOSTS", "127.0.0.1,localhost,0.0.0.0,testserver"
).split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "widget_tweaks",
    "accounts",
    "core",
    "stock",
    "intelligence",
    "audit",
    "reports",
    "notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "audit.middleware.AuditoriaMiddleware",
]

ROOT_URLCONF = "estoque.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.global_context",
            ],
        },
    },
]

WSGI_APPLICATION = "estoque.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / os.environ.get("DATABASE_URL", "db.sqlite3"),
    }
}

# Permite trocar para PostgreSQL via .env: DATABASE_URL=postgres://USER:PASS@HOST:PORT/NAME
# Exemplo:
#   DATABASE_URL=postgres://estoque:senha@localhost:5432/estoque
#   DATABASE_URL=postgresql://estoque:senha@localhost:5432/estoque
db_url = os.environ.get("DATABASE_URL")
if db_url and (db_url.startswith("postgres://") or db_url.startswith("postgresql://")):
    import dj_database_url
    DATABASES["default"] = dj_database_url.parse(
        db_url, conn_max_age=600, conn_health_checks=True,
    )
    # Força o engine psycopg v3 (recomendado em Django 5+)
    DATABASES["default"]["ENGINE"] = "django.db.backends.postgresql"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 6}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Web Push (VAPID) — geradas em runtime se não definidas
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY")
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY")
VAPID_CLAIMS_SUB = os.environ.get("VAPID_CLAIMS_SUB", "mailto:admin@estoque.local")

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

# Custom user model
AUTH_USER_MODEL = "auth.User"

# Messages tags styled for Tailwind
from django.contrib.messages import constants as message_constants
MESSAGE_TAGS = {
    message_constants.DEBUG: "bg-gray-100 text-gray-800 border-gray-300",
    message_constants.INFO: "bg-blue-50 text-blue-800 border-blue-300",
    message_constants.SUCCESS: "bg-green-50 text-green-800 border-green-300",
    message_constants.WARNING: "bg-yellow-50 text-yellow-800 border-yellow-300",
    message_constants.ERROR: "bg-red-50 text-red-800 border-red-300",
}
