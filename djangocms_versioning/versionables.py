from django.apps import apps
from django.db.models.base import Model


def _cms_extension():
    return apps.get_app_config("djangocms_versioning").cms_extension


def _to_model(model_or_obj):
    if isinstance(model_or_obj, Model):
        model_or_obj = model_or_obj.__class__
    return model_or_obj


def for_content(model_or_obj):
    """Get the registered VersionableItem instance for a content model or content model instance"""
    return _cms_extension().versionables_by_content[_to_model(model_or_obj)]


def for_grouper(model_or_obj):
    """Get the registered VersionableItem instance for a grouper model or grouper model instance"""
    return _cms_extension().versionables_by_grouper[_to_model(model_or_obj)]


def exists_for_content(model_or_obj):
    """Test for registered VersionableItem for a content model or content model instance"""
    return _to_model(model_or_obj) in _cms_extension().versionables_by_content


def exists_for_grouper(model_or_obj):
    """Test for registered VersionableItem for a grouper model or grouper model instance"""
    return _to_model(model_or_obj) in _cms_extension().versionables_by_grouper
