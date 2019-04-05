from celery import shared_task
import celery
import time
from django.core import management

@celery.task
def harvestSocrata():
    try:
        management.call_command("harvestSocrata")
        return "success"
    except:
        print(e)
