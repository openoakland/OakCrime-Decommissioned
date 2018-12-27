from django import template

from django.template.defaultfilters import stringfilter

register = template.Library()

# If you’re writing a template filter that only expects a string as the
# first argument, you should use the decorator stringfilter. This will
# convert an object to its string value before being passed to your
# function.
	
@register.filter
@stringfilter
def startswith(value, arg):
    """Usage, {% if value|starts_with:"arg" %}"""
    return value.startswith(arg)

