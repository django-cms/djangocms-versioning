import collections

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import cached_property

from cms.app_base import CMSAppConfig, CMSAppExtension
from cms.models import PageContent, Placeholder

from .datastructures import VersionableItem
from .helpers import register_versionadmin_proxy, replace_admin_for_models


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
            # NOTE: Do not use the cached property here as this is
            # still changing and needs to be calculated on the fly
            registered_so_far = [v.content_model for v in self.versionables]
            if versionable.content_model in registered_so_far:
                raise ImproperlyConfigured(
                    "{!r} has already been registered".format(versionable.content_model))
            # Checks passed. Add versionable to our master list
            self.versionables.append(versionable)

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

    def configure_app(self, cms_config):
        self.handle_versioning_setting(cms_config)
        self.handle_admin_classes(cms_config)
        self.handle_version_admin(cms_config)


def copy_page_content(original_content):
    """Copy the PageContent object and deepcopy its
    placeholders and plugins
    """
    # Copy content object
    content_fields = {
        field.name: getattr(original_content, field.name)
        for field in PageContent._meta.fields
        # don't copy primary key because we're creating a new obj
        if PageContent._meta.pk.name != field.name
    }
    new_content = PageContent.objects.create(**content_fields)

    # Copy placeholders
    new_placeholders = []
    for placeholder in original_content.placeholders.all():
        placeholder_fields = {
            field.name: getattr(placeholder, field.name)
            for field in Placeholder._meta.fields
            # don't copy primary key because we're creating a new obj
            # and handle the source field later
            if field.name not in [Placeholder._meta.pk.name, 'source']
        }
        if placeholder.source:
            placeholder_fields['source'] = new_content
        new_placeholder = Placeholder.objects.create(**placeholder_fields)
        # Copy plugins
        placeholder.copy_plugins(new_placeholder)
        new_placeholders.append(new_placeholder)
    new_content.placeholders.add(*new_placeholders)

    return new_content


class VersioningCMSConfig(CMSAppConfig):
    """Implement versioning for core cms models
    """
    djangocms_versioning_enabled = getattr(
        settings, 'VERSIONING_CMS_MODELS_ENABLED', True)
    versioning = [
        VersionableItem(
            content_model=PageContent,
            grouper_field_name='page',
            copy_function=copy_page_content,
        ),
    ]
