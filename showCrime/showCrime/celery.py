from __future__ import absolute_import

import os
import django
from celery import Celery


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'showCrime.settings')

app = Celery('showCrime')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


# https://stackoverflow.com/a/30903271
#
# from django.conf import settings
#
# # set the default Django settings module for the 'celery' program.
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'showCrime.settings')
# django.setup()
#
# app = Celery('showCrime')
# app.config_from_object('django.conf:settings')
# app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))


from django_celery_beat.models import IntervalSchedule
schedule, created = IntervalSchedule.objects.get_or_create( \
	name='harvestSocrata', \
	every=24, \
	period=IntervalSchedule.HOURS, \
	)
