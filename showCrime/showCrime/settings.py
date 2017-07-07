"""
Django settings for showCrime project.

django wrapper for https://www.openoakland.org/oakcrimedata/

updated 23 Mar 17
to include GIS

init build from 'django-admin startproject' using Django 1.10.5.
"""

__author__ = "rik@electronicArtifacts.com", "actionspeakslouder@gmail.com"
__version__ = "0.2"


import os
import socket

# deployment alternatives
HostName = socket.gethostname()
if HostName.startswith('hancock'):
	# Local
	DEBUG = True
	ALLOWED_HOSTS = ['localhost']
	
	INTERNAL_IPS = ['127.0.0.1']
	
	keyFile = '/Users/rik/hacks/showCrime_secretKey.txt'
	# memcacheFile = '/Data/virtualenv/django/memcached.sock'

	# Static files (CSS, JavaScript, Images)
	# https://docs.djangoproject.com/en/1.10/howto/static-files/
	STATIC_URL = '/static/'

	PlotPath = "/Data/sharedData/c4a_oakland/djOakData_plots/"
	SiteURL = 'localhost:/showCrime'
	
elif HostName.find('webfaction') != -1:
	# Webfactions
	DEBUG = True # False  
	ALLOWED_HOSTS = ['oakcrime.org']
	keyFile = '/home/rik/hacks/showCrime_secretKey.txt'
	# memcacheFile = '$HOME/memcached.sock'

	# https://docs.webfaction.com/software/django/config.html#serving-django-static-media
	STATIC_URL = 'http://oakcrime.org/static/'
	STATIC_ROOT = '/home/rik/webapps/djstatic/'
	
	PlotPath = "/home/rik/webapps/eastatic/oakDataPlots/"
	SiteURL = 'oakcrime.org/showCrime'

else:
	import sys
	sys.exit('Unknown deployment host?! %s' % (HostName))

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
with open(keyFile) as f:
	SECRET_KEY = f.read().strip()

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'django.contrib.gis',
    'rest_framework',
    'leaflet',
    
    # 'django_cron',    # Tivix django_cron
    
    'dailyIncid'
]

MIDDLEWARE = [
	
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

]

# if DEBUG:
#         INSTALLED_APPS.append('debug_toolbar')

# 	# The order of MIDDLEWARE_CLASSES is important. You should include the
# 	# Debug Toolbar middleware as early as possible in the list. However, it
# 	# must come after any other middleware that encodes the response's
# 	# content, such as GZipMiddleware.
#         MIDDLEWARE.insert(0,'debug_toolbar.middleware.DebugToolbarMiddleware')

ROOT_URLCONF = 'showCrime.urls'

TEMPLATES = [
    {
		'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        
 		# not allowed to have APP_DIRS true when using explicit loaders
       'APP_DIRS': True,
       
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
				
			# 2do: fix error
			# ImportError: Module "showCrime" does not define a "ExtentionLoader" attribute/class
			# loaders should be a list of strings or tuples, where each represents a template loader class.
# 			'loaders': [
# 				'showCrime.ExtentionLoader',
# 				'django.template.loaders.filesystem.Loader',
# 				'django.template.loaders.app_directories.Loader',
# 			],	

        },
    },
]

WSGI_APPLICATION = 'showCrime.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases


DATABASES = {
    'default': {
            # LOCAL
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
		'NAME': 'oakcrime',
		'USER': os.getenv('SHOWCRIME_DB_USER', 'rik'),
		'PASSWORD': os.getenv('SHOWCRIME_DB_PASS', 'xxxx'),
		'HOST': os.getenv('SHOWCRIME_DB_HOST', 'localhost')

        # webfaction database specfics
#         # 'ENGINE': 'django.contrib.gis.db.backends.postgis_psycopg2',
#         'ENGINE': 'django.contrib.gis.db.backends.postgis',
#         'NAME': 'djdb10',
#         'USER': 'rik',
#         # 2do: separate database password
#         'PASSWORD': 'xxxx',
#         'HOST': '127.0.0.1',

    },
}

# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

# USE_TZ = True
#
# The PostgreSQL backend stores datetimes as timestamp with time
# zone. In practice, this means it converts datetimes from the
# connection's time zone to UTC on storage, and from UTC to the
# connection's time zone on retrieval.  As a consequence, if you're
# using PostgreSQL, you can switch between USE_TZ = False ...

USE_TZ = False

LOGIN_URL = '/dailyIncid/need2login/'
LOGIN_REDIRECT_URL = '/dailyIncid/'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'propagate': True,
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'dailyIncid': {
            'handlers': ['console', 'mail_admins'],
            'level': 'INFO',
        }
    }
}

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAdminUser',
    ],
    'PAGE_SIZE': 10
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

DEBUG_TOOLBAR_PATCH_SETTINGS = False
# DEBUG_TOOLBAR_CONFIG = {
#     'SHOW_TOOLBAR_CALLBACK': lambda r: False,  # disables DEBUG_TOOLBAR
# }

print('settings: HostName', HostName)
print('settings: baseDir', BASE_DIR)
print('settings: templates.dirs',TEMPLATES[0]["DIRS"])
