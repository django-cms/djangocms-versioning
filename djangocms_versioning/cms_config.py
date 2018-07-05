from cms.app_base import CMSAppConfig, CMSAppExtension
from django.core.exceptions import ImproperlyConfigured


class VersioningCMSExtension(CMSAppExtension):

    def __init__(self):
        self.version_models = []

    def configure_app(self, cms_config):

        if hasattr(cms_config, 'versioning_models'):
            if not isinstance(cms_config.versioning_models, list):
                raise ImproperlyConfigured(
                    "versioning_models must be defined in cms_config.py")
            else:
                if cms_config.versioning_models:
                    self.version_models.extend(cms_config.versioning_models)

        else:

            raise ImproperlyConfigured(
                "versioning_models must be defined in cms_config.py"
            )

    def get_version_models(self):
        print("self.version_models : ", self.version_models)
        if not isinstance(self.version_models, list):
            print("Version models not a list")
        return self.version_models

