"""
Django settings for monprojet project.
"""

import os
from importlib.util import find_spec
from pathlib import Path

from dotenv import load_dotenv

if find_spec('dj_database_url') is not None:
    import dj_database_url
else:
    dj_database_url = None

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env', override=True)

# Security-sensitive settings are read from the environment in production and
# fall back to development-friendly defaults locally.
SECRET_KEY = os.getenv(
    'SECRET_KEY',
    'django-insecure-$3w2av1@$q3da2(74_%am*1iw7eiz-()#3@cii6rqc%-6ul4ru',
)

# DEBUG defaults to True locally; set DEBUG=False in the host's environment.
DEBUG = os.getenv('DEBUG', 'True').strip().lower() in ('1', 'true', 'yes', 'on')

# Comma-separated list in the environment, e.g. ALLOWED_HOSTS=example.com,www.example.com
ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv(
        'ALLOWED_HOSTS', '192.168.11.23,192.168.11.22,localhost,127.0.0.1'
    ).split(',')
    if h.strip()
]

RENDER_EXTERNAL_HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME', '').strip()
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# When deployed behind a TLS-terminating proxy (most hosts), trust forwarded
# origins/headers. Configure CSRF_TRUSTED_ORIGINS=https://yourdomain in the env.
if not DEBUG:
    CSRF_TRUSTED_ORIGINS = [
        o.strip()
        for o in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',')
        if o.strip()
    ]
    if RENDER_EXTERNAL_HOSTNAME:
        CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_EXTERNAL_HOSTNAME}')
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True').strip().lower() in (
        '1', 'true', 'yes', 'on',
    )
    SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '0') or '0')
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').strip().lower() in ('1', 'true', 'yes', 'on')
    CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'False').strip().lower() in ('1', 'true', 'yes', 'on')

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '').strip()
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()
GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID', '').strip()
GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET', '').strip()

GOOGLE_AUTH_CONFIGURED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
GITHUB_AUTH_CONFIGURED = bool(GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET)
SOCIAL_AUTH_CONFIGURED = GOOGLE_AUTH_CONFIGURED or GITHUB_AUTH_CONFIGURED

HAS_ALLAUTH = SOCIAL_AUTH_CONFIGURED and all(
    find_spec(module) is not None
    for module in (
        'allauth',
        'allauth.account',
        'allauth.socialaccount',
        'requests',
        'cryptography',
    )
)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'app1',
]

if HAS_ALLAUTH:
    INSTALLED_APPS += [
        'django.contrib.sites',
        'allauth',
        'allauth.account',
        'allauth.socialaccount',
    ]
    if GOOGLE_AUTH_CONFIGURED:
        INSTALLED_APPS.append('allauth.socialaccount.providers.google')
    if GITHUB_AUTH_CONFIGURED:
        INSTALLED_APPS.append('allauth.socialaccount.providers.github')

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

if HAS_ALLAUTH:
    AUTHENTICATION_BACKENDS.append(
        'allauth.account.auth_backends.AuthenticationBackend'
    )

LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/candidate/signin'
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True

if HAS_ALLAUTH:
    ACCOUNT_ADAPTER = 'app1.adapters.NoMessagesAccountAdapter'
    SOCIALACCOUNT_ADAPTER = 'app1.adapters.NoMessagesSocialAccountAdapter'
    SOCIALACCOUNT_PROVIDERS = {}
    if GOOGLE_AUTH_CONFIGURED:
        SOCIALACCOUNT_PROVIDERS['google'] = {
            'APPS': [
                {
                    'client_id': GOOGLE_CLIENT_ID,
                    'secret': GOOGLE_CLIENT_SECRET,
                    'key': '',
                }
            ],
            'SCOPE': ['profile', 'email'],
            'AUTH_PARAMS': {'access_type': 'online'},
            'OAUTH_PKCE_ENABLED': True,
        }
    if GITHUB_AUTH_CONFIGURED:
        SOCIALACCOUNT_PROVIDERS['github'] = {
            'APPS': [
                {
                    'client_id': GITHUB_CLIENT_ID,
                    'secret': GITHUB_CLIENT_SECRET,
                    'key': '',
                }
            ],
            'SCOPE': ['user:email'],
        }

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'app1.middleware.AdminEnglishMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if find_spec('whitenoise') is not None:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

if HAS_ALLAUTH:
    MIDDLEWARE.append('allauth.account.middleware.AccountMiddleware')

ROOT_URLCONF = 'monprojet.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'monprojet.wsgi.application'

# Database — DATABASE_URL for hosted Postgres, MySQL when DB_NAME is configured,
# otherwise SQLite for local development.
DATABASE_URL = os.getenv('DATABASE_URL', '').strip()
if DATABASE_URL:
    if dj_database_url is None:
        raise RuntimeError('DATABASE_URL is set but dj-database-url is not installed.')
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
elif os.getenv('DB_NAME', '').strip():
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.getenv('DB_NAME', '').strip(),
            'USER': os.getenv('DB_USER', '').strip(),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', '').strip() or '127.0.0.1',
            'PORT': os.getenv('DB_PORT', '').strip() or '3306',
            'OPTIONS': {
                'charset': 'utf8mb4',
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
# Target dir for `python manage.py collectstatic` in production.
STATIC_ROOT = BASE_DIR / 'staticfiles'
if not DEBUG and find_spec('whitenoise') is not None:
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email — console backend by default (local/dev & offline presentation);
# configure real SMTP via the environment in production.
EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587') or '587')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').strip().lower() in (
    '1', 'true', 'yes', 'on',
)
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@managerahub.ma')

# Allow embedding media/pages in iframes from the same origin (needed for offline PDF previews)
X_FRAME_OPTIONS = 'SAMEORIGIN'

SITE_URL = os.getenv('SITE_URL', 'http://127.0.0.1:8000').rstrip('/')
