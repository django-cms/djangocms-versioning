import collections

from django.core.exceptions import ImproperlyConfigured

from cms.app_base import CMSAppExtension

from .helpers import replace_admin_for_models
from .versionable import Versionable, VersionableList


class VersioningCMSExtension(CMSAppExtension):

    def __init__(self):
        self.versionables = VersionableList()

    def handle_versioning_setting(self, cms_config):
        """Check the versioning setting has been correctly set
        and add the models to the masterlist if all is ok
        """
        # First check that versioning is correctly defined
        if not hasattr(cms_config, 'versioning'):
            raise ImproperlyConfigured(
                "versioning must be defined in cms_config.py")
        if not isinstance(cms_config.versioning, collections.abc.Iterable):
            raise ImproperlyConfigured(
                "versioning not defined as an iterable")
        for versionable in cms_config.versioning:
            if not isinstance(versionable, Versionable):
                raise ImproperlyConfigured(
                    "{!r} is not a subclass of djangocms_versioning.Versionable".format(versionable))
        # If no exceptions raised, we can now add the versioned models
        # into our masterlist
        self.versionables.extend(cms_config.versioning)

    def handle_admin_classes(self, cms_config):
        """Replaces admin model classes for all registered content types
        with an admin model class that inherits from VersioningAdminMixin.
        """
        replace_admin_for_models(
            VersionableList(cms_config.versioning).by_content.keys(),
        )

    def configure_app(self, cms_config):
        self.handle_versioning_setting(cms_config)
        self.handle_admin_classes(cms_config)
