from django import template

from ..helpers import version_list_url

register = template.Library()


@register.filter
def url_version_list(content):
    return version_list_url(content)
