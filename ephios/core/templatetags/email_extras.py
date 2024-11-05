import base64

from django import template
from django.contrib.staticfiles import finders
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag()
def base64_static_file(path):
    result = finders.find(path)
    with open(result, "rb") as file:
        data = file.read()
    base64_data = base64.b64encode(data).decode()
    return mark_safe(base64_data)
