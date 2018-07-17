import collections

from django.core.exceptions import ImproperlyConfigured

from cms.app_base import CMSAppConfig, CMSAppExtension

from .helpers import replace_admin_for_models
from .models import BaseVersion


class VersioningCMSExtension(CMSAppExtension):

    def __init__(self):
        self._version_models = []
        self.content_to_version_models = {}

    def handle_versioning_models_setting(self, cms_config):
        """Check the versioning_models setting has been correctly set
        and add the models to the masterlist if all is ok
        """
        # First check that versioning_models is correctly defined
        if not hasattr(cms_config, 'versioning_models'):
            raise ImproperlyConfigured(
                "versioning_models must be defined in cms_config.py")
        if not isinstance(cms_config.versioning_models, collections.abc.Iterable):
            raise ImproperlyConfigured(
                "versioning_models not defined as a list")
        for model in cms_config.versioning_models:
            try:
                is_versioning_model = issubclass(model, BaseVersion)
            except TypeError:
                raise ImproperlyConfigured(
                    "elements in versioning_models must be model classes")
            if not is_versioning_model:
                raise ImproperlyConfigured(
                    "models in versioning_models must inherit from BaseVersion")
        # If no exceptions raised, we can now add the versioning models
        # into our masterlist
        self._version_models.extend(cms_config.versioning_models)
        # Based on the versioning models list, create a helper
        # attribute that we can derive
        content_models = [
            model._meta.get_field('content').rel.model
            for model in cms_config.versioning_models
        ]
        self.content_to_version_models.update({
            content: version
            for content, version
            in zip(content_models, cms_config.versioning_models)
        })

    def handle_admin_classes(self, cms_config):
        """Replaces admin model classes for all registered content types
        with an admin model class that inherits from VersioningAdminMixin
        """

        replace_admin_for_models(self.content_to_version_models.keys())

    def configure_app(self, cms_config):
        self.handle_versioning_models_setting(cms_config)
        self.handle_admin_classes(cms_config)

