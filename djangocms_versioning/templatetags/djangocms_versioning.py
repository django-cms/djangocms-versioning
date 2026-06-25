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


def _get_version(content):
    """Return the (single) version of a versioned content object.

    Uses a prefetched ``versions`` list when one is available - ``prefetched_versions``
    on changelist/menu querysets, ``_prefetched_versions`` on grouper change views -
    and falls back to a query otherwise (e.g. the toolbar). Each content object has a
    single version, so the first entry is the relevant one.

    The callers only ever receive versioned content objects (a grouper instance,
    which has no ``versions`` manager, is filtered out by the templates), so the
    query fallback is safe.
    """
    for attr in ("prefetched_versions", "_prefetched_versions"):
        prefetched = getattr(content, attr, None)
        if prefetched is not None:
            return prefetched[0] if prefetched else None
    return content.versions.first()


@register.filter
def url_version_list(content):
    return version_list_url(content)


@register.filter
def url_publish_version(content, user):
    version = _get_version(content)
    if version and version.check_publish.as_bool(user) and version.can_be_published():
        proxy_model = versionables.for_content(content).version_model_proxy
        return reverse(
            f"admin:{proxy_model._meta.app_label}_{proxy_model.__name__.lower()}_publish",
            args=(version.pk,),
        )
    return ""


@register.filter
def url_new_draft(content, user):
    version = _get_version(content)
    if version and version.state == constants.PUBLISHED:
        proxy_model = versionables.for_content(content).version_model_proxy
        return reverse(
            f"admin:{proxy_model._meta.app_label}_{proxy_model.__name__.lower()}_edit_redirect",
            args=(version.pk,),
        )
    return ""


@register.filter
def url_revert_version(content, user):
    version = _get_version(content)
    if version and version.check_revert.as_bool(user):
        proxy_model = versionables.for_content(content).version_model_proxy
        return reverse(
            f"admin:{proxy_model._meta.app_label}_{proxy_model.__name__.lower()}_revert",
            args=(version.pk,),
        )
    return ""
