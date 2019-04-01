from django.apps import apps
from django.db.models.base import Model


def _cms_extension():
    return apps.get_app_config("djangocms_versioning").cms_extension


def for_content(model_or_obj):
    """Get the registered VersionableItem instance for a content model or content model instance"""
    if isinstance(model_or_obj, Model):
        model_or_obj = model_or_obj.__class__
    return _cms_extension().versionables_by_content[model_or_obj]


def for_grouper(model_or_obj):
    """Get the registered VersionableItem instance for a grouper model or grouper model instance"""
    if isinstance(model_or_obj, Model):
        model_or_obj = model_or_obj.__class__
    return _cms_extension().versionables_by_grouper[model_or_obj]
