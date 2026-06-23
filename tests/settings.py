"""Django settings for running the djangocms-versioning test suite.

This is a self-contained settings module (no django-app-helper required).
It is used by pytest via the ``DJANGO_SETTINGS_MODULE`` set in
``pyproject.toml``'s ``[tool.pytest.ini_options]`` section.

The database can be overridden through the ``DATABASE_URL`` environment
variable (e.g. for the postgres/mysql CI matrix); when unset an in-memory
SQLite database is used.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

SECRET_KEY = "djangocms-versioning-test-suite"

DEBUG = True

SITE_ID = 1

ROOT_URLCONF = "tests.urls"

USE_TZ = False
TIME_ZONE = "America/Chicago"

# Database -------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

if os.environ.get("DATABASE_URL"):
    import dj_database_url

    DATABASES["default"] = dj_database_url.parse(os.environ["DATABASE_URL"])

# Applications ---------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "djangocms_admin_style",
    "django.contrib.admin",
    "django.contrib.messages",
    "cms",
    "menus",
    "sekizai",
    "treebeard",
    "djangocms_text",
    "djangocms_versioning",
    "djangocms_versioning.test_utils.extensions",
    "djangocms_versioning.test_utils.polls",
    "djangocms_versioning.test_utils.blogpost",
    "djangocms_versioning.test_utils.text",
    "djangocms_versioning.test_utils.people",
    "djangocms_versioning.test_utils.incorrectly_configured_blogpost",
    "djangocms_versioning.test_utils.unversioned_editable_app",
    "djangocms_versioning.test_utils.extended_polls",
]

MIDDLEWARE = [
    "django.middleware.http.ConditionalGetMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "cms.middleware.language.LanguageCookieMiddleware",
    "cms.middleware.user.CurrentUserMiddleware",
    "cms.middleware.page.CurrentPageMiddleware",
    "cms.middleware.toolbar.ToolbarMiddleware",
]

# Templates ------------------------------------------------------------------

TEMPLATES = [
    {
        "NAME": "django",
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "django.template.context_processors.csrf",
                "django.template.context_processors.debug",
                "django.template.context_processors.tz",
                "django.template.context_processors.request",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "cms.context_processors.cms_settings",
                "sekizai.context_processors.sekizai",
            ],
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
        },
    },
]

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

STATIC_URL = "/static/"
MEDIA_URL = "/media/"
STATIC_ROOT = BASE_DIR / "static"
MEDIA_ROOT = BASE_DIR / "media"

# Internationalisation -------------------------------------------------------

LANGUAGE_CODE = "en"

LANGUAGES = (
    ("en", "English"),
    ("de", "German"),
    ("fr", "French"),
    ("it", "Italiano"),
)

# django CMS -----------------------------------------------------------------

CMS_TEMPLATES = (
    ("fullwidth.html", "Fullwidth"),
    ("page.html", "Normal page"),
)

CMS_PERMISSION = True

CMS_CONFIRM_VERSION4 = True

CMS_LANGUAGES = {
    1: [
        {"code": "en", "name": "English", "fallbacks": ["de", "fr"]},
        {
            "code": "de",
            "name": "Deutsche",
            "fallbacks": ["en"],  # FOR TESTING DO NOT ADD 'fr' HERE
        },
        {
            "code": "fr",
            "name": "Française",
            "fallbacks": ["en"],  # FOR TESTING DO NOT ADD 'de' HERE
        },
        {
            "code": "it",
            "name": "Italiano",
            "fallbacks": ["fr"],  # FOR TESTING, LEAVE AS ONLY 'fr'
        },
    ]
}

PARLER_ENABLE_CACHING = False

DJANGOCMS_VERSIONING_ENABLE_MENU_REGISTRATION = True

# Misc -----------------------------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
