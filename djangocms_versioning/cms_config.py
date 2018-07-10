import collections

from django.core.exceptions import ImproperlyConfigured

from cms.app_base import CMSAppConfig, CMSAppExtension

from .helpers import replace_admin_for_models

from cms.app_base import CMSAppConfig, CMSAppExtension
from django.core.exceptions import ImproperlyConfigured


class VersioningCMSExtension(CMSAppExtension):

    def __init__(self):
        self._version_models = []

    def handle_versioning_models_setting(self, cms_config):
        if not hasattr(cms_config, 'versioning_models'):
            raise ImproperlyConfigured(
                "versioning_models must be defined in cms_config.py")
        if not isinstance(cms_config.versioning_models, collections.abc.Iterable):
            raise ImproperlyConfigured(
                "versioning_models not defined as a list")
        elif cms_config.versioning_models:
            self._version_models.extend(cms_config.versioning_models)

    def configure_app(self, cms_config):
        # stub function created to help integrate with Kzrysztof code later
        self.handle_versioning_models_setting(cms_config)
        content_model_n = [model._meta.get_field('content').rel.model for model in cms_config.versioning_models]
        replace_admin_for_models(content_model_n)

    def get_version_models(self):
        return self._version_models

