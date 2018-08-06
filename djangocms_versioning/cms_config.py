import collections

from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import cached_property

from cms.app_base import CMSAppExtension

from .datastructures import VersionableItem
from .helpers import replace_admin_for_models


class VersioningCMSExtension(CMSAppExtension):

    def __init__(self):
        self.versionables = []

    @cached_property
    def versionables_by_content(self):
        return {versionable.content_model: versionable for versionable in self.versionables}

    def handle_versioning_setting(self, cms_config):
        """Check the versioning setting has been correctly set
        and add it to the masterlist if all is ok
        """
        # First check that versioning is defined and is an iterable
        if not hasattr(cms_config, 'versioning'):
            raise ImproperlyConfigured(
                "versioning must be defined in cms_config.py")
        if not isinstance(cms_config.versioning, collections.abc.Iterable):
            raise ImproperlyConfigured(
                "versioning not defined as an iterable")
        for versionable in cms_config.versioning:
            # Now check each item in the iterable is a VersionableItem
            if not isinstance(versionable, VersionableItem):
                raise ImproperlyConfigured(
                    "{!r} is not a subclass of djangocms_versioning.datastructures.VersionableItem".format(versionable))
            # ...and has copy functions provided for all foreign keys on content
            fk_rels = [
                f.name for f in versionable.content_model._meta.fields
                if f.is_relation and not f.name == versionable.grouper_field_name
            ]
            fk_reverse_rels = [
                "%s.%s" % (f.name, f.field.name)
                for f in versionable.content_model._meta.related_objects
            ]
            # ...and copy functions for all m2m relationships
            m2m_rels = [
                f.name for f in versionable.content_model._meta.many_to_many
            ]
            content_rels = fk_rels + m2m_rels + fk_reverse_rels
            for rel in content_rels:
                if rel not in versionable.copy_functions:
                    raise ImproperlyConfigured(
                        "%s.%s needs to have a copy method provided in cms_config.py"
                        % (versionable.content_model.__name__, rel))
        # All checks passed, we can add it to our masterlist now
        self.versionables.extend(cms_config.versioning)

    def handle_admin_classes(self, cms_config):
        """Replaces admin model classes for all registered content types
        with an admin model class that inherits from VersioningAdminMixin.
        """
        replace_admin_for_models(
            [versionable.content_model for versionable in cms_config.versioning],
        )

    def configure_app(self, cms_config):
        self.handle_versioning_setting(cms_config)
        self.handle_admin_classes(cms_config)
