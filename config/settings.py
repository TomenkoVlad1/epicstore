import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# читаємо змінні з файлу .env (він НЕ заливається на github)
load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=''):
    return [x.strip() for x in os.environ.get(name, default).split(',') if x.strip()]


TESTING = 'test' in sys.argv

# ---------------- безпека ----------------

# за замовчуванням DEBUG вимкнений - вмикаємо тільки локально через .env
DEBUG = env_bool('DJANGO_DEBUG', False)

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if DEBUG or TESTING:
        SECRET_KEY = 'django-insecure-only-for-local-development'
    else:
        raise ImproperlyConfigured('Задайте DJANGO_SECRET_KEY в .env або змінних середовища')

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS')

SESSION_COOKIE_HTTPONLY = True          # js не може прочитати кукі сесії
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'                # сайт не можна вставити в iframe (захист від clickjacking)

# вмикати тільки коли сайт реально працює по https
if env_bool('DJANGO_USE_HTTPS', False):
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# rate limiting (вимикаємо під час тестів)
RATELIMIT_ENABLED = env_bool('RATELIMIT_ENABLED', not TESTING)
RATELIMIT_GLOBAL_PER_MINUTE = int(os.environ.get('RATELIMIT_GLOBAL_PER_MINUTE', 300))
RATELIMIT_TRUST_X_FORWARDED_FOR = env_bool('RATELIMIT_TRUST_X_FORWARDED_FOR', False)


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',  # має стояти перед staticfiles
    'django.contrib.staticfiles',

    # мої додатки
    'core',
    'catalog',
    'users',
    'cart',
    'library',
    'social',
    'news',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',      # віддає статику в продакшені
    'core.middleware.GlobalRateLimitMiddleware',       # захист від флуду
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'users.middleware.LastSeenMiddleware',  # статус онлайн
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

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
                # мої
                'cart.context_processors.cart',
                'catalog.context_processors.recently_viewed',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get('SQLITE_PATH', BASE_DIR / 'db.sqlite3'),
    }
}


# ---------------- кеш ----------------
# якщо задано REDIS_URL - кеш в Redis, інакше в пам'яті (зручно локально на Windows)
REDIS_URL = os.environ.get('REDIS_URL')

if TESTING:
    CACHES = {'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}
elif REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
            'TIMEOUT': 60 * 15,
            'KEY_PREFIX': 'epicstore',
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'TIMEOUT': 60 * 15,
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'uk'

TIME_ZONE = 'Europe/Kyiv'

USE_I18N = True

USE_TZ = True


# ---------------- статика і медіа ----------------
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'   # сюди collectstatic збирає все для продакшену

MEDIA_URL = 'media/'
MEDIA_ROOT = Path(os.environ.get('MEDIA_ROOT', BASE_DIR / 'media'))
# в продакшені медіа зазвичай віддає nginx, але для навчального docker можна і django
SERVE_MEDIA = env_bool('SERVE_MEDIA', False)

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        # в продакшені whitenoise стискає файли і додає хеш до назви (для кешу браузера)
        'BACKEND': (
            'django.contrib.staticfiles.storage.StaticFilesStorage'
            if DEBUG or TESTING
            else 'whitenoise.storage.CompressedManifestStaticFilesStorage'
        ),
    },
}

# максимальний розмір аватарки, байт
MAX_AVATAR_SIZE = 2 * 1024 * 1024

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# свій юзер замість стандартного
AUTH_USER_MODEL = 'users.CustomUser'

LOGIN_URL = 'users:login'
LOGIN_REDIRECT_URL = 'catalog:home'
LOGOUT_REDIRECT_URL = 'catalog:home'

# помилки в продакшені пишемо в консоль (docker logs їх покаже)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'WARNING'},
}
