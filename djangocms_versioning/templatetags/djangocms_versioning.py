import django
from django import template
from django.urls import reverse

from .. import constants, versionables
from ..helpers import version_list_url

register = template.Library()


@register.simple_tag
def object_tools_outside_content():
    """Whether the admin ``object-tools`` block is rendered outside the
    ``content`` block. Django moved it out of ``content`` in 6.1 (see Django
    ticket #36331), so templates that override ``content`` must render their
    tools in a different slot depending on the Django version."""
    return django.VERSION >= (6, 1)


@register.filter
def url_version_list(content):
    return version_list_url(content)


@register.filter
def url_publish_version(content, user):
    if hasattr(content, "prefetched_versions"):
        version = content.prefetched_versions[0]
    else:
        version = content.versions.first()
    if version:
        if version.check_publish.as_bool(user) and version.can_be_published():
            proxy_model = versionables.for_content(content).version_model_proxy
            return reverse(
                f"admin:{proxy_model._meta.app_label}_{proxy_model.__name__.lower()}_publish",
                args=(version.pk,),
            )
    return ""


@register.filter
def url_new_draft(content, user):
    if hasattr(content, "prefetched_versions"):
        version = content.prefetched_versions[0]
    else:
        version = content.versions.first()
    if version:
        if version.state == constants.PUBLISHED:
            proxy_model = versionables.for_content(content).version_model_proxy
            return reverse(
                f"admin:{proxy_model._meta.app_label}_{proxy_model.__name__.lower()}_edit_redirect",
                args=(version.pk,),
            )
    return ""


@register.filter
def url_revert_version(content, user):
    if hasattr(content, "prefetched_versions"):
        version = content.prefetched_versions[0]
    else:
        version = content.versions.first()
    if version:
        if version.check_revert.as_bool(user):
            proxy_model = versionables.for_content(content).version_model_proxy
            return reverse(
                f"admin:{proxy_model._meta.app_label}_{proxy_model.__name__.lower()}_revert",
                args=(version.pk,),
            )
    return ""
