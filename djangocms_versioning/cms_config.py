import collections

from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import cached_property

from cms.app_base import CMSAppConfig, CMSAppExtension
from cms.models import PageContent

from .datastructures import VersionableItem, default_copy
from .helpers import (
    inject_generic_relation_to_version,
    register_versionadmin_proxy,
    replace_admin_for_models,
    replace_default_manager,
)


class VersioningCMSExtension(CMSAppExtension):

    def __init__(self):
        self.versionables = []

    @cached_property
    def versionables_by_content(self):
        return {versionable.content_model: versionable for versionable in self.versionables}

    def is_content_model_versioned(self, content_model):
        """Checks if provided content model supports versioning.
        """
        return content_model in self.versionables_by_content

    @cached_property
    def versionables_by_grouper(self):
        return {versionable.grouper_model: versionable for versionable in self.versionables}

    def is_grouper_model_versioned(self, grouper_model):
        return grouper_model in self.versionables_by_grouper

    def handle_versioning_setting(self, cms_config):
        """Check the versioning setting has been correctly set
        and add it to the masterlist if all is ok
        """
        # First check that versioning is correctly defined
        if not hasattr(cms_config, 'versioning'):
            raise ImproperlyConfigured(
                "versioning must be defined in cms_config.py")
        if not isinstance(cms_config.versioning, collections.abc.Iterable):
            raise ImproperlyConfigured(
                "versioning not defined as an iterable")
        for versionable in cms_config.versioning:
            if not isinstance(versionable, VersionableItem):
                raise ImproperlyConfigured(
                    "{!r} is not a subclass of djangocms_versioning.datastructures.VersionableItem".format(versionable))
        self.versionables.extend(cms_config.versioning)

    def handle_admin_classes(self, cms_config):
        """Replaces admin model classes for all registered content types
        with an admin model class that inherits from VersioningAdminMixin.
        """
        replace_admin_for_models(
            [versionable.content_model for versionable in cms_config.versioning],
        )

    def handle_version_admin(self, cms_config):
        """
        Registers version admin for all registered content types
        with filtering by content type applied, so only versions for
        that specific content type are shown.
        """
        for versionable in cms_config.versioning:
            register_versionadmin_proxy(versionable)

    def handle_content_model_generic_relation(self, cms_config):
        """Adds `versions` GenericRelation field to all provided
        content models.
        """
        for versionable in cms_config.versioning:
            inject_generic_relation_to_version(versionable.content_model)

    def handle_content_model_manager(self, cms_config):
        """Replaces default manager in provided content models with
        one inheriting from PublishedContentManagerMixin.
        """
        for versionable in cms_config.versioning:
            replace_default_manager(versionable.content_model)

    def configure_app(self, cms_config):
        self.handle_versioning_setting(cms_config)
        self.handle_admin_classes(cms_config)
        self.handle_version_admin(cms_config)
        self.handle_content_model_generic_relation(cms_config)
        self.handle_content_model_manager(cms_config)


class VersioningCMSConfig(CMSAppConfig):
    djangocms_versioning_enabled = True
    versioning = [
        VersionableItem(
            content_model=PageContent,
            grouper_field_name='page',
            copy_function=default_copy,
        ),
    ]
