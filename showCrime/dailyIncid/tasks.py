from celery import shared_task
import celery
import time
from django.core import management

celery = celery.Celery('tasks')

import os
os.environ[ 'DJANGO_SETTINGS_MODULE' ] = "showCrime.settings"

@celery.task
def harvestSocrata():
    try:
        management.call_command("harvestSocrata")
        return "success"
    except:
        print(e)
