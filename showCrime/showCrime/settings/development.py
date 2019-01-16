from .base import *

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
