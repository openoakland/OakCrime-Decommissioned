'''
Created on Oct 30, 2017

@author: rik
'''

from django.core.management.base import BaseCommand

class Command(BaseCommand):
	help = 'command description goes here...'
	def add_arguments(self, parser):
		parser.add_argument('startDate', nargs='?', default='noStartSpecified') 

	def handle(self, *args, **options):

		pass
	
