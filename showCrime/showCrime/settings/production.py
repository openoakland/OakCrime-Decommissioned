from .base import *

# Email config, ala https://docs.webfaction.com/software/django/getting-started.html?highlight=django%2520email#configuring-django-to-send-email-messages
ADMIN = ((env('ADMIN_USER'),env('ADMIN_EMAIL')))
EMAIL_HOST = env('EMAIL_HOST')
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD  = env('EMAIL_PW')
SERVER_EMAIL = env('SERVER_EMAIL')
