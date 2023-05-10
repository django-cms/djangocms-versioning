from cms.extensions.models import BaseExtension
from cms.operations import (
    ADD_PLUGIN,
    ADD_PLUGINS_FROM_PLACEHOLDER,
    CHANGE_PLUGIN,
    CLEAR_PLACEHOLDER,
    CUT_PLUGIN,
    DELETE_PLUGIN,
    MOVE_PLUGIN,
    PASTE_PLACEHOLDER,
    PASTE_PLUGIN,
)
from django.utils import timezone

from .models import Version
from .versionables import _cms_extension


def _update_modified(instance):
    if isinstance(instance, BaseExtension):
        instance = instance.extended_object
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
    instance = kwargs["obj"].get_content_obj()
    _update_modified(instance)


def update_modified_date_for_placeholder_source(sender, **kwargs):
    placeholders = []
    operation = kwargs["operation"]
    if operation in (ADD_PLUGIN, CHANGE_PLUGIN, CLEAR_PLACEHOLDER, DELETE_PLUGIN):
        placeholders = [kwargs["placeholder"]]
    elif operation in (ADD_PLUGINS_FROM_PLACEHOLDER, PASTE_PLACEHOLDER, PASTE_PLUGIN):
        placeholders = [kwargs["target_placeholder"]]
    elif operation in (CUT_PLUGIN,):
        placeholders = [kwargs["source_placeholder"]]
    elif operation in (MOVE_PLUGIN,):
        placeholders = [kwargs["source_placeholder"], kwargs["target_placeholder"]]

    for placeholder in placeholders:
        _update_modified(placeholder.source)
