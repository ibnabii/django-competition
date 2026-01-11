# import logging.config
from pathlib import Path

import environ
from django.contrib.messages import constants as messages
from django.core.management.utils import get_random_secret_key
from django.urls import reverse_lazy

env = environ.Env()
environ.Env.read_env()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY", default=get_random_secret_key())

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG", default=False)
TEST_ENV = env("TEST_ENV", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=["http://127.0.0.1"])
DEFAULT_DOMAIN = env("DEFAULT_DOMAIN")

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "contest",
    "tinymce",
    # 'django.contrib.sites',
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    # 'allauth.socialaccount.providers.google',
    # 'allauth.socialaccount.providers.facebook',
    # "bootstrap5", # django-bootstrap-v5==1.0.11
    "django_bootstrap5",
    "django_bootstrap_icons",
    "rosetta",
    # "captcha",  # in djagno_recaptcha 3.0.0
    "django_recaptcha",  # since djagno_recaptcha 4.0.0
    "django_countries",
    "simple_history",
    "paypal.standard.ipn",
    "widget_tweaks",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    # 'crum.CurrentRequestUserMiddleware',
    "simple_history.middleware.HistoryRequestMiddleware",
]

if DEBUG:
    MIDDLEWARE.append("debug_toolbar.middleware.DebugToolbarMiddleware")
    INSTALLED_APPS.append("debug_toolbar")

AUTHENTICATION_BACKENDS = [
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
]
AUTH_USER_MODEL = "contest.User"

ROOT_URLCONF = "tacom.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "contest.context_processors.test_env",
            ],
        },
    },
]

WSGI_APPLICATION = "tacom.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

if env("DB_USE_SQLITE", default=True):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": env.db(),
    }

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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

# Paths
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/contest/profile"
# LOCALE_PATHS = (BASE_DIR / 'locale/', )
STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATIC_ROOT = BASE_DIR / "serving_static"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en"

TIME_ZONE = "Europe/Warsaw"

USE_I18N = True

LANGUAGES = [("pl", "Polski"), ("en", "English"), ("es", "Español")]

# RemovedInDjango50Warning:
# The default value of USE_TZ will change from False to True in Django 5.0.
# Set USE_TZ to False in your project settings if you want to keep the current default behavior.
USE_TZ = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/


# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


SITE_ID = 1

# Logging
# settings.py


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,  # Keeps Django's default loggers
    "handlers": {
        "console": {  # This handler will output logs to the console
            "class": "logging.StreamHandler",
            "level": "INFO",  # Minimum log level to capture
        },
    },
    "loggers": {
        # Custom logger for "models"
        "models": {  # This logger corresponds to getLogger("models")
            "handlers": ["console"],  # Use the 'console' handler
            "level": "INFO",  # Minimum level to capture (DEBUG, INFO, WARNING, etc.)
            "propagate": False,  # Avoid propagating to the root logger
        },
        "views": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        # Django's default loggers can be configured here as well
        # 'django': {
        #     'handlers': ['console'],  # You can also output Django logs to the console
        #     'level': 'INFO',
        #     'propagate': True,
        # },
    },
    # 'root': {
    #     'handlers': ['console'],
    #     'level': 'WARNING',  # Root logger config (captures all warnings by default)
    # },
}

# Testing
TESTING_LOCALES = ["zh_CN", "uk_UA", "pl_PL", "es_ES", "en_US"]

# TinyMCE settings
TINYMCE_DEFAULT_CONFIG = {
    "theme": "silver",
    "height": 500,
    "menubar": "edit insert view format table tools",
    "plugins": "advlist,autolink,lists,link,image,charmap,print,preview,anchor,"
    "searchreplace,visualblocks,code,fullscreen,insertdatetime,media,table,paste,"
    "code,help,wordcount",
    "toolbar": "undo redo | formatselect | "
    "bold italic backcolor | alignleft aligncenter "
    "alignright alignjustify | bullist numlist outdent indent | "
    "removeformat | help",
}

# Allauth settings

# ACCOUNT_AUTHENTICATION_METHOD = "email"
# ACCOUNT_EMAIL_REQUIRED = True
# ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = {"email*", "password1*", "password2*"}

ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_USER_MODEL_EMAIL_FIELD = "email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"

# TODO: delete here and  above
# ACCOUNT_USERNAME_MIN_LENGTH = 3
# ACCOUNT_USERNAME_BLACKLIST = ["admin", "user", "username"]

ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True

SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True

ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = reverse_lazy(
    "contest:profile_edit"
)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env("EMAIL_PORT")
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = env("EMAIL_HOST_USER")
# override default signup form to add gdpr checkbox
ACCOUNT_FORMS = {
    "signup": "contest.forms.CustomSignupForm",
}

# Debug_toolbar
INTERNAL_IPS = [
    "127.0.0.1",
]

# bootstrap messages
MESSAGE_TAGS = {
    messages.DEBUG: "alert-secondary",
    messages.INFO: "alert-info",
    messages.SUCCESS: "alert-success",
    messages.WARNING: "alert-warning",
    messages.ERROR: "alert-danger",
}

BOOTSTRAP5 = {
    "css_url": "/static/bootstrap.min.css",
}

# ReCaptcha
if TEST_ENV:
    SILENCED_SYSTEM_CHECKS = ["django_recaptcha.recaptcha_test_key_error"]
else:
    RECAPTCHA_PRIVATE_KEY = env("RECAPTCHA_PRIVATE_KEY")
    RECAPTCHA_PUBLIC_KEY = env("RECAPTCHA_PUBLIC_KEY")


# Countries
COUNTRIES_FIRST = ["PL"]

# PayU
PAYU_POS_ID = env("PAYU_POS_ID")
PAYU_MD5 = env("PAYU_MD5")
PAYU_CLIENT_ID = env("PAYU_CLIENT_ID")
PAYU_CLIENT_SECRET = env("PAYU_CLIENT_SECRET")
PAYU_URL = env("PAYU_URL")
PAYU_PROD_HOSTS = [
    "185.68.12.10",
    "185.68.12.11",
    "185.68.12.12",
    "185.68.12.26",
    "185.68.12.27",
    "185.68.12.28",
]
PAYU_TEST_HOSTS = [
    "185.68.14.10",
    "185.68.14.11",
    "185.68.14.12",
    "185.68.14.26",
    "185.68.14.27",
    "185.68.14.28",
]

ALLOWED_HOSTS += PAYU_TEST_HOSTS

# PayPal
PAYPAL_RECEIVER_EMAIL = env("PAYPAL_RECEIVER_EMAIL")
PAYPAL_TEST = env("PAYPAL_TEST", default=False)
