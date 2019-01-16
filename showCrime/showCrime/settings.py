"""
django app for https://OakCrime.org
"""

__author__ = "rik@electronicArtifacts.com"
__credits__ = ["clinton.blackburn@gmail.com","actionspeakslouder@gmail.com"]
__date__ = "181217"
__version__ = "0.3"

import environ
import dj_database_url

# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
root = environ.Path(__file__) - 2
env = environ.Env(DEBUG=(bool, False), )

import os


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

# NOTE: This setting assumes all requests are proxied through a web server (e.g. nginx). If that is not the case,
# ensure this is set to a more restrictive value. See https://docs.djangoproject.com/en/1.11/ref/settings/#allowed-hosts
# for more information.
ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = [
	'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
    'django.contrib.sites',
	'django.contrib.messages',
	'django.contrib.staticfiles',
    'django.contrib.flatpages',
	'django.contrib.gis',
	'rest_framework',
    'dailyIncid',
]

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

# PUBLIC_ROOT = env('PUBLIC_ROOT')
MEDIA_ROOT = os.path.join(root, "media") 
MEDIA_URL = '/media/'
STATIC_ROOT = root("static") 
STATIC_URL = '/static/'

if DEBUG:
	INSTALLED_APPS.append('debug_toolbar')

	# The order of MIDDLEWARE_CLASSES is important. You should include the
	# Debug Toolbar middleware as early as possible in the list. However, it
	# must come after any other middleware that encodes the response's
	# content, such as GZipMiddleware.
	MIDDLEWARE.insert(0,'debug_toolbar.middleware.DebugToolbarMiddleware')
	STATICFILES_DIRS = [ ]
	INTERNAL_IPS = ['127.0.0.1' ] # for debug_toolbar
else:
	STATICFILES_DIRS = [ env('STATICFILES_DIRS'), ]
	INTERNAL_IPS = []


ROOT_URLCONF = 'showCrime.urls'

TEMPLATES = [
	{
		'BACKEND': 'django.template.backends.django.DjangoTemplates',
		'DIRS': [os.path.join(root, 'templates')],
		
 		# not allowed to have APP_DIRS true when using explicit loaders
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
	'default': dj_database_url.config()
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

# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

# https://docs.djangoproject.com/en/2.1/topics/i18n/timezones/#database
# ... if you’re using PostgreSQL, you can switch between USE_TZ = False and USE_TZ = True freely.
# The database connection’s time zone will be set to TIME_ZONE or UTC respectively, so that Django obtains correct datetimes in all cases.
# You don’t need to perform any data conversions
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/


SITE_ID = 1

CACHES = {
    'default': env.cache(default='locmemcache://showCrime'),
}

# 2do: enable logging, but excluding INFO from boxsdk, ...

# def generate_file_handler(filename):
#     """ Generates a logging handler that writes to a file.
# 
#     If the `ENABLE_LOGGING_TO_FILE` setting is `False`, `logging.NullHandler` will be used instead
#     of `logging.FileHandler`.
# 
#     Args:
#         filename (str): Name of the file to which logs are written.
# 
#     Returns:
#         dict
#     """
#     handler = {
#         'level': 'INFO',
#         'formatter': 'standard',
#     }
#     if ENABLE_LOGGING_TO_FILE:
#         handler.update({
#             'class': 'logging.FileHandler',
#             'filename': environ.Path(LOG_FILE_PATH).path(filename),
#         })
#     else:
#         handler['class'] = 'logging.NullHandler'
# 
#     return handler
# 
# 
# LOG_FILE_PATH = os.path.join(root, "logs") 
# ENABLE_LOGGING_TO_FILE = env('ENABLE_LOGGING_TO_FILE', cast=bool, default=True)
# LOGGING = {
# 	'version': 1,
# 	'formatters': {
#         'standard': {
#             'format': '%(asctime)s %(levelname)s %(process)d %(pathname)s:%(lineno)d - %(message)s',
# 		},
# 	},
# 	'handlers': {
# 		'console': {
# 			'level': 'INFO',
# 			'class': 'logging.StreamHandler',
#             'formatter': 'standard'
# 		},
#         'file_app': generate_file_handler('app.log'),
#         'null': {
#             'class': 'logging.NullHandler',
# 		}
# 	},
# 	'loggers': {
#         '': {
#             'handlers': ['file_app', 'console', ],
#             'level': 'INFO',
# 			'propagate': True,
# 		},
# 		},
# 		'dailyIncid': {
# 			'handlers': ['console', 'mail_admins'],
# 			'level': 'INFO',
# 		}
# 	}

REST_FRAMEWORK = {
	'DEFAULT_PERMISSION_CLASSES': [
		'rest_framework.permissions.IsAuthenticated', # 'rest_framework.permissions.IsAdminUser',
	],
	'PAGE_SIZE': 10,
	'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
}


LEAFLET_CONFIG = {
  'DEFAULT_CENTER': (52.00,20.00),
  'DEFAULT_ZOOM': 6,
  'MIN_ZOOM': 1,
  'MAX_ZOOM': 20,
}

CRON_CLASSES = [
	"dailyIncid.cron.HarvestSocrataJob",
	'django_cron.cron.FailedRunsNotificationCronJob',
]

# Email config, ala https://docs.webfaction.com/software/django/getting-started.html?highlight=django%2520email#configuring-django-to-send-email-messages
#ADMIN = ((env('ADMIN_USER'),env('ADMIN_EMAIL')))
#EMAIL_HOST = env('EMAIL_HOST')
#EMAIL_HOST_USER = env('EMAIL_HOST_USER')
#EMAIL_HOST_PASSWORD  = env('EMAIL_PW')
#SERVER_EMAIL = env('SERVER_EMAIL')
SITE_URL = env('SITE_URL')

DEBUG_TOOLBAR_PATCH_SETTINGS = False
# disables DEBUG_TOOLBAR
# DEBUG_TOOLBAR_CONFIG = {
#	 'SHOW_TOOLBAR_CALLBACK': lambda r: False,  }

LOG_FILE_PATH = os.path.join(root, "logs") 
PLOT_PATH = os.path.join(root, "plots") 

###################
# echo settings

import django
print('settings: django version',django.__version__)
print('settings: DEBUG',DEBUG)

import socket
HostName = socket.gethostname()
print('settings: HostName', HostName)
print('settings: root', root)
print('settings: STATIC_URL', STATIC_URL)
print('settings: SITE_URL', SITE_URL)
print('settings: STATICFILES_DIRS', STATICFILES_DIRS)
print('settings: MEDIA_ROOT', MEDIA_ROOT)
print('settings: LOG_FILE_PATH', LOG_FILE_PATH)
print('settings: PLOT_PATH', PLOT_PATH)
print('settings: database hosted at %s:%s' % (DATABASES['default']["HOST"],DATABASES['default']["NAME"]))
print('settings: DEBUG',DEBUG)


