import os
import re
import environ
from pathlib import Path
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False)
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

CELERY_BROKER_URL = env("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND")
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "corsheaders",
    "rest_framework",
    "viewflow",
    "django_celery_beat",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "pos",
    "api",
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
    "simple_history.middleware.HistoryRequestMiddleware",
    "rollbar.contrib.django.middleware.RollbarNotifierMiddleware",
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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB"),
        "USER": env("POSTGRES_USER"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        "HOST": env("POSTGRES_HOST"),
        "PORT": env("POSTGRES_PORT"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    STATIC_ROOT = BASE_DIR / "staticfiles"
    CORS_ALLOWED_ORIGINS = [
        "https://myfrontend.com",
        "https://another-frontend.com",
    ]
    CORS_ALLOW_CREDENTIALS = True
    CORS_ALLOW_HEADERS = [
        "Authorization",
    ]

CELERY_BEAT_SCHEDULE = {
    "archive-created-orders-every-hour": {
        "task": "archive_created_orders",
        "schedule": crontab(minute=0, hour="*"),
    },
    "daily-orders-report": {
        "task": "daily_orders_report",
        "schedule": crontab(hour=22, minute=0),
    },
}

LOGGING = {
	"version": 1,
	"disable_existing_loggers": False,
	"formatters": {
		"json": {
			"()": "pythonjsonlogger.json.JsonFormatter",
			"format": "%(asctime)s %(levelname)s %(name)s %(message)s"
		}
	},
	"handlers": {
		"console": {
			"class": "logging.StreamHandler",
			"formatter": "json"
		},
		"rollbar": {
			"class": "rollbar.logger.RollbarHandler",
			"level": "WARNING"
		},
	},
	"loggers": {
		"": {
			"handlers": ["console", "rollbar"],
			"level": "INFO",
            "propagate": True
		}
	}
}

ROLLBAR = {
    "access_token": env("ROLLBAR_TOKEN"),
    "environment": "development" if DEBUG else "production",
    "code_version": "1.0",
    "root": BASE_DIR,
    "ignorable_404_urls": (re.compile(r'.*\.(php|asp|aspx|cgi|bak|old|sql|tar|gz)$'),),
}

LANGUAGE_CODE = "ru-ru"

TIME_ZONE = "Asia/Yekaterinburg"

USE_I18N = True

USE_L10N = False

USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
