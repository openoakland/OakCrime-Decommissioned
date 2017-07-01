# from https://www.djangosnippets.org/snippets/10489/
# 150522

from os.path import dirname, join, abspath, isdir
 
from django.template.loaders.base import Loader as BaseLoader
from django.core.exceptions import ImproperlyConfigured
from django.template import TemplateDoesNotExist
from django.conf import settings
from django.utils._os import safe_join

from django.apps import apps

class ExtentionLoader(BaseLoader):
	'''This is especially useful for overriding the admin templates without
	having to symlink or copy them into your project. For example 
	{% extends "admin:base.html" %} would extend the admin page base.html.
	'''
	is_usable = True
 
	def get_template_sources(self, template_name, template_dirs=None):
		app_name, template_name = template_name.split(":", 1)
		try:
			template_dir = abspath(safe_join(dirname(apps.get_app_config(app_name).__file__), 'templates'))
		except ImproperlyConfigured:
			raise TemplateDoesNotExist()
		
		return template_name, template_dir
	 
	def load_template_source(self, template_name, template_dirs=None):
		""" 
		Template loader that only serves templates from specific app's template directory.
		Works for template_names in format app_label:some/template/name.html
		"""
		if ":" not in template_name:
			raise TemplateDoesNotExist()
	 
		template_name, template_dir = self.get_template_sources(template_name)
	 
		if not isdir(template_dir):
			raise TemplateDoesNotExist()
		
		filepath = safe_join(template_dir, template_name)
		with open(filepath, 'rb') as fp:
			return (fp.read().decode(settings.FILE_CHARSET), filepath)

	 
	load_template_source.is_usable = True
