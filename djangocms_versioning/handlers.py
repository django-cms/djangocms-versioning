from django.utils import timezone

from .models import Version
from .versionables import _cms_extension


def _update_modified(instance):
    if instance and _cms_extension().is_content_model_versioned(instance.__class__):
        try:
            version = Version.objects.get_for_content(instance)
        except Version.DoesNotExist:
            return
        version.modified = timezone.now()
        version.save(update_fields=["modified"])


def update_modified_date(sender, **kwargs):
    if kwargs["created"]:
        return
    _update_modified(kwargs["instance"])


def update_modified_date_for_pagecontent(sender, **kwargs):
    instance = kwargs["obj"].get_title_obj()
    _update_modified(instance)


def update_modified_date_for_placeholder_source(sender, **kwargs):
    placeholder = kwargs["placeholder"]
    _update_modified(placeholder.source)
