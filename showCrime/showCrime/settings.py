import os

import environ

project_root = environ.Path(__file__) - 2
env = environ.Env(DEBUG=(bool, False), )

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

# NOTE: This setting assumes all requests are proxied through a web server (e.g. nginx). If that is not the case,
# ensure this is set to a more restrictive value. See https://docs.djangoproject.com/en/1.11/ref/settings/#allowed-hosts
# for more information.
ALLOWED_HOSTS = ['*']

# Application definition

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.flatpages',
    'django.contrib.gis',
]

THIRD_PARTY_APPS = [
    'rest_framework',
]

LOCAL_APPS = [
    'dailyIncid',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
]

ROOT_URLCONF = 'showCrime.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            str(project_root.path('templates')),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.i18n',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'showCrime.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASES = {
    'default': env.db(),
}

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

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

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
]

# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

PUBLIC_ROOT = env('PUBLIC_ROOT', cast=str, default=str(project_root.path('public')))
MEDIA_ROOT = str(environ.Path(PUBLIC_ROOT).path('media'))
MEDIA_URL = '/media/'
STATIC_ROOT = str(environ.Path(PUBLIC_ROOT).path('static'))
STATIC_URL = '/static/'

STATICFILES_DIRS = [
    str(project_root.path('static')),
]

SITE_ID = 1

CACHES = {
    'default': env.cache(default='locmemcache://showCrime'),
}


def generate_file_handler(filename):
    """ Generates a logging handler that writes to a file.

    If the `ENABLE_LOGGING_TO_FILE` setting is `False`, `logging.NullHandler` will be used instead
    of `logging.FileHandler`.

    Args:
        filename (str): Name of the file to which logs are written.

    Returns:
        dict
    """
    handler = {
        'level': 'INFO',
        'formatter': 'standard',
    }
    if ENABLE_LOGGING_TO_FILE:
        handler.update({
            'class': 'logging.FileHandler',
            'filename': environ.Path(LOG_FILE_PATH).path(filename),
        })
    else:
        handler['class'] = 'logging.NullHandler'

    return handler


LOG_FILE_PATH = env('LOG_FILE_PATH', cast=str, default=str(project_root.path('logs')))
ENABLE_LOGGING_TO_FILE = env('ENABLE_LOGGING_TO_FILE', cast=bool, default=False)
LOGGING = {
    'version': 1,
    'formatters': {
        'standard': {
            'format': '%(asctime)s %(levelname)s %(process)d %(pathname)s:%(lineno)d - %(message)s',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
        'file_app': generate_file_handler('app.log'),
        'null': {
            'class': 'logging.NullHandler',
        }
    },
    'loggers': {
        '': {
            'handlers': ['file_app', 'console', ],
            'level': 'INFO',
            'propagate': True,
        },
        'boxsdk': {
            'handlers': ['file_app', 'console'],
            'level': 'WARNING',
            'propagate': True,
        },
        'django': {
            'handlers': ['console'],
            'propagate': True,
        },
    },
}

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'PAGE_SIZE': 10,
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
}

LEAFLET_CONFIG = {
    'DEFAULT_CENTER': (52.00, 20.00),
    'DEFAULT_ZOOM': 6,
    'MIN_ZOOM': 1,
    'MAX_ZOOM': 20,
}

PLOT_PATH = os.path.join(project_root, 'plots')

# Email configuration
SERVER_EMAIL = env('SERVER_EMAIL')
EMAIL_CONFIG = env.email_url('EMAIL_URL')
vars().update(EMAIL_CONFIG)
