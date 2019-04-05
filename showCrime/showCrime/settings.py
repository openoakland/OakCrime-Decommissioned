"""
django app for https://OakCrime.org
"""

__author__ = "rik@electronicArtifacts.com"
__credits__ = ["clinton.blackburn@gmail.com","actionspeakslouder@gmail.com"]
__date__ = "190128"
__version__ = "0.1.0-alpha"

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
	'django_celery_beat',
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
            'handlers': ['file_app'],
            'level': 'INFO',
        },
        'dailyIncid': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'handlers': ['console'],
        },
        'showCrime': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'handlers': ['console'],
        },
        'boxsdk': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
        'django': {
            'handlers': ['console'],
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

# Box SDK configuration
BOX_ENTERPRISE_ID = env('BoxEnterpriseID', default=None)
BOX_CLIENT_ID = env('BoxClientID', default=None)
BOX_CLIENT_SECRET = env('BoxClientSecret', default=None)
BOX_JWT_KEY_ID = env('BoxPublicKeyID', default=None)
BOX_RSA_FILE_PATH = env('BoxRSAFile', default=None)
BOX_RSA_FILE_PASSPHRASE = env('BoxPassPhrase', default=None)

GOOGLE_MAPS_API_KEY = env('GoogleMapAPIKey', default=None)

# Celery config

# CELERY_BROKER_URL = 'amqp://guest:guest@localhost:5672//'
# https://kombu.readthedocs.io/en/latest/userguide/connections.html#connection-urls
# A connection without options will use the default connection settings,
# which is using the localhost host, default port, user name guest,
# password guest and virtual host “/”. A connection without arguments is
# the same as: Connection('amqp://guest:guest@localhost:5672//')

CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_RESULT_BACKEND = 'rabbitmq'

###################
# echo settings
#
# import django
# print('settings: django version',django.__version__)
# print('settings: DEBUG',DEBUG)
#
# import socket
# HostName = socket.gethostname()
# print('settings: HostName', HostName)
# print('settings: root', root)
# print('settings: STATIC_URL', STATIC_URL)
# print('settings: SITE_URL', SITE_URL)
# print('settings: STATICFILES_DIRS', STATICFILES_DIRS)
# print('settings: MEDIA_ROOT', MEDIA_ROOT)
# print('settings: LOG_FILE_PATH', LOG_FILE_PATH)
# print('settings: PLOT_PATH', PLOT_PATH)
# print('settings: database hosted at %s:%s' % (DATABASES['default']["HOST"],DATABASES['default']["NAME"]))
# print('settings: DEBUG',DEBUG)
