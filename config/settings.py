"""
Django settings for config project.

Works locally (SQLite, local Redis, DEBUG on) and on Render (PostgreSQL via
DATABASE_URL, settings from environment variables).
"""

import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path):
    """Tiny .env reader for local development. Real environment variables always win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(BASE_DIR / ".env")

# Render sets the RENDER environment variable automatically.
IS_RENDER = "RENDER" in os.environ


# =========================
# CORE / SECURITY
# =========================

# Locally a throwaway key is used. On Render the key MUST come from the
# SECRET_KEY environment variable (never commit a real key to GitHub).
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if IS_RENDER:
        raise RuntimeError("SECRET_KEY environment variable is not set.")
    SECRET_KEY = "dev-only-insecure-key-do-not-use-in-production"

# DEBUG is on locally and off on Render unless DEBUG=True is set explicitly.
DEBUG = os.getenv("DEBUG", "False" if IS_RENDER else "True").lower() == "true"

ALLOWED_HOSTS = ["localhost", "127.0.0.1", ".onrender.com"]

_render_host = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if _render_host:
    ALLOWED_HOSTS.append(_render_host)

# Extra hosts, comma separated, for a custom domain later.
ALLOWED_HOSTS += [h.strip() for h in os.getenv("EXTRA_ALLOWED_HOSTS", "").split(",") if h.strip()]

CSRF_TRUSTED_ORIGINS = ["https://*.onrender.com"]
# Custom domain later, e.g. CSRF_EXTRA_ORIGINS=https://app.example.com
CSRF_TRUSTED_ORIGINS += [o.strip() for o in os.getenv("CSRF_EXTRA_ORIGINS", "").split(",") if o.strip()]

if IS_RENDER:
    # Render terminates HTTPS in front of the app.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# =========================
# APPLICATIONS
# =========================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'core',
    'data_engineering',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# =========================
# DATABASE
# =========================

# DATABASE_URL present (Render / Neon / Supabase)  -> PostgreSQL
# DATABASE_URL absent (your laptop)                -> SQLite
if os.getenv("DATABASE_URL"):
    DATABASES = {
        'default': dj_database_url.config(conn_max_age=600),
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# =========================
# REST FRAMEWORK
# =========================

_renderers = ['rest_framework.renderers.JSONRenderer']
if DEBUG:
    _renderers.append('rest_framework.renderers.BrowsableAPIRenderer')

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': _renderers,
    # Missing model files -> HTTP 503 with a clear message instead of a 500.
    'EXCEPTION_HANDLER': 'core.exceptions.api_exception_handler',
}


# =========================
# PASSWORD VALIDATION
# =========================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# =========================
# INTERNATIONALIZATION
# =========================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# =========================
# STATIC FILES (WhiteNoise)
# =========================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}


# =========================
# EMAIL
# =========================

# The app does not send email. Console backend for local dev only; in production
# the backend is left unset (Django then defaults to SMTP), which also keeps
# `manage.py check --deploy` from failing with mail.E001.
if DEBUG:
    MAILERS = {
        'default': {
            'BACKEND': 'django.core.mail.backends.console.EmailBackend',
        },
    }
else:
    MAILERS = {'default': {}}


# =========================
# LOGGING
# =========================

# With DEBUG=False Django's default config prints NO tracebacks to the console
# (it only tries to email admins), so 500 errors would be invisible in the
# Render / Railway logs. Send everything to stdout instead.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {'handlers': ['console'], 'level': os.getenv('LOG_LEVEL', 'INFO')},
    'loggers': {
        'django': {'handlers': ['console'], 'level': os.getenv('LOG_LEVEL', 'INFO'), 'propagate': False},
    },
}


# =========================
# REDIS / CELERY / CACHE
# =========================

# Local: Redis on your machine.
# Render: set CELERY_BROKER_URL / CELERY_RESULT_BACKEND (and REDIS_URL for the
# cache) to the Render Key Value connection URL. On the free demo without Redis,
# leave them unset: the cache falls back to in-memory and Celery is simply unused.
_local_redis = "redis://127.0.0.1:6379"

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", f"{_local_redis}/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", f"{_local_redis}/0")
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

CELERY_BEAT_SCHEDULE = {
    "run-data-pipeline-every-5-minutes": {
        "task": "data_engineering.tasks.run_data_pipeline",
        "schedule": 5 * 60,
    },
    "check-model-drift-every-15-minutes": {
        "task": "data_engineering.tasks.check_model_and_retrain",
        "schedule": 15 * 60,
    },
}

_cache_redis_url = os.getenv("REDIS_URL") or (None if IS_RENDER else f"{_local_redis}/1")

if _cache_redis_url:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _cache_redis_url,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }