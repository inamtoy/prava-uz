"""Prava.uz loyihasi sozlamalari."""

import sys
from pathlib import Path

from decouple import Csv, config
from django.templatetags.static import static
from django.urls import reverse_lazy

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="django-insecure-dev-only-change-me")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="127.0.0.1,localhost", cast=Csv())

INSTALLED_APPS = [
    # unfold django.contrib.admin dan OLDIN turishi shart (admin.site ni almashtiradi)
    "unfold",
    "unfold.contrib.filters",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "quiz",
    "results",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Ma'lumotlar bazasi: DB_ENGINE=postgres (asosiy) yoki sqlite (lokal tez ishga tushirish).
# `manage.py test` sukut bo'yicha SQLite'da ishlaydi (tezlik uchun); Postgres'da sinash: TEST_DB_ENGINE=postgres.
DB_ENGINE = config("DB_ENGINE", default="sqlite")
RUNNING_TESTS = len(sys.argv) > 1 and sys.argv[1] == "test"
if RUNNING_TESTS:
    DB_ENGINE = config("TEST_DB_ENGINE", default="sqlite")

if DB_ENGINE == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME", default="prava_uz"),
            "USER": config("DB_USER", default="prava"),
            "PASSWORD": config("DB_PASSWORD", default=""),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="5432"),
            "CONN_MAX_AGE": config("DB_CONN_MAX_AGE", default=60, cast=int),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["accounts.backends.EmailOrUsernameBackend"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "uz"
# unfold o'zbekcha katalogsiz keladi — tarjimalar locale/uz/ da (tools/compile_messages.py)
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "profile"  # amalda rolga qarab: accounts.views.redirect_url_for
LOGOUT_REDIRECT_URL = "home"

# Imtihon qoidalari
EXAM_QUESTION_COUNT = 20
EXAM_DURATION_SECONDS = 25 * 60
EXAM_MAX_MISTAKES = 2
PRACTICE_QUESTION_COUNT = 20

if not DEBUG:
    SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())


# ---------------------------------------------------------------------------
# Admin panel (django-unfold) — dizayn manbasi: design/admin/ (Stitch)
# ---------------------------------------------------------------------------
UNFOLD = {
    "SITE_TITLE": "Prava.uz boshqaruv paneli",
    "SITE_HEADER": "Prava.uz",
    "SITE_SUBHEADER": "Boshqaruv paneli",
    "SITE_URL": "/",
    "SITE_ICON": lambda request: static("img/logo.svg"),
    "SITE_SYMBOL": "traffic",
    "SITE_FAVICONS": [{"rel": "icon", "type": "image/svg+xml", "href": lambda request: static("img/logo.svg")}],
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "DASHBOARD_CALLBACK": "results.dashboard.dashboard_callback",
    "STYLES": [lambda request: static("css/admin.css")],
    "BORDER_RADIUS": "10px",
    "COLORS": {
        # Saytdagi tokenlar: --ink-900 #0B1B33 ... --bg #F4F6FA
        "base": {
            "50": "#F4F6FA", "100": "#EEF1F6", "200": "#E6EAF0", "300": "#CBD5E1",
            "400": "#A9B4C6", "500": "#7D8BA3", "600": "#51627E", "700": "#3A4A66",
            "800": "#1E3355", "900": "#132541", "950": "#0B1B33",
        },
        # --primary #2457F5 (600)
        "primary": {
            "50": "#EEF2FF", "100": "#E0E7FF", "200": "#C7D3FE", "300": "#A3B6FC",
            "400": "#6F8DF9", "500": "#4570F7", "600": "#2457F5", "700": "#1B45D1",
            "800": "#1A3AA8", "900": "#1B3584", "950": "#142250",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Asosiy",
                "items": [
                    {"title": "Boshqaruv paneli", "icon": "dashboard", "link": reverse_lazy("admin:index")},
                ],
            },
            {
                "title": "Kontent",
                "items": [
                    {"title": "Mavzular", "icon": "menu_book", "link": reverse_lazy("admin:quiz_topic_changelist")},
                    {"title": "Savollar", "icon": "quiz", "link": reverse_lazy("admin:quiz_question_changelist")},
                ],
            },
            {
                "title": "Natijalar",
                "items": [
                    {"title": "Imtihonlar", "icon": "assignment", "link": reverse_lazy("admin:results_exam_changelist")},
                ],
            },
            {
                "title": "Foydalanuvchilar",
                "items": [
                    {"title": "Foydalanuvchilar", "icon": "group", "link": reverse_lazy("admin:accounts_user_changelist")},
                ],
            },
            {
                "title": "Sayt",
                "items": [
                    {"title": "Saytni ochish", "icon": "open_in_new", "link": "/", "active": False},
                ],
            },
        ],
    },
}
