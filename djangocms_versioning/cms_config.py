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

    def is_content_model_versioned(self, content_model):
        """Checks if provided content model supports versioning.
        """
        return content_model in self.versionables_by_content

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
            # ...and has copy functions provided for all relationships on content
            generic_rels = [
                f.name for f in versionable.content_model._meta.virtual_fields
                if f.is_relation
            ]
            fk_rels = [
                f.name for f in versionable.content_model._meta.fields
                if f.is_relation
                # don't include the grouper FK - that doesn't need a copy method
                and not f.name == versionable.grouper_field_name
                # don't include the content type fk of generic keys
                # if the model has a generic fk then we only need a copy
                # method for generic fk field itself
                and f.name not in [versionable.content_model._meta.get_field(rel_name).ct_field for rel_name in generic_rels]
            ]
            m2m_rels = [
                f.name for f in versionable.content_model._meta.many_to_many
            ]
            reverse_rels = [
                "%s.%s" % (f.name, f.field.name)
                # _meta.related_objects contains data for both fk and m2m rels
                for f in versionable.content_model._meta.related_objects
            ]
            content_rels = fk_rels + m2m_rels + reverse_rels + generic_rels
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
