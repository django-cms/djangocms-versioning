import collections

from django.conf import settings
from django.contrib.admin.utils import flatten_fieldsets
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from cms.app_base import CMSAppConfig, CMSAppExtension
from cms.models import PageContent, Placeholder
from cms.utils.i18n import get_language_tuple

from .admin import VersioningAdminMixin
from .datastructures import BaseVersionableItem, VersionableItem
from .helpers import (
    inject_generic_relation_to_version,
    register_versionadmin_proxy,
    replace_admin_for_models,
    replace_default_manager,
)
from .models import Version


class VersioningCMSExtension(CMSAppExtension):
    def __init__(self):
        self.versionables = []
        self.add_to_context = {}

    @cached_property
    def versionables_by_content(self):
        """Returns a dict of {content_model_cls: VersionableItem obj}"""
        return {
            versionable.content_model: versionable for versionable in self.versionables
        }

    def is_content_model_versioned(self, content_model):
        """Returns if the content model is registered for versioning.
        """
        return content_model in self.versionables_by_content

    @cached_property
    def versionables_by_grouper(self):
        """Returns a dict of {grouper_model_cls: VersionableItem obj}"""
        return {
            versionable.grouper_model: versionable
            for versionable in self.versionables
            # TODO: Comment on/document why this is here
            if versionable.concrete
        }

    def is_grouper_model_versioned(self, grouper_model):
        """Returns if the grouper model has been registered for versioning"""
        return grouper_model in self.versionables_by_grouper

    def handle_versioning_setting(self, cms_config):
        """Check the versioning setting has been correctly set
        and add it to the masterlist if all is ok
        """
        # First check that versioning is correctly defined
        if not isinstance(cms_config.versioning, collections.abc.Iterable):
            raise ImproperlyConfigured("versioning not defined as an iterable")
        for versionable in cms_config.versioning:
            if not isinstance(versionable, BaseVersionableItem):
                raise ImproperlyConfigured(
                    "{!r} is not a subclass of djangocms_versioning.datastructures.BaseVersionableItem".format(
                        versionable
                    )
                )
            # NOTE: Do not use the cached property here as this is
            # still changing and needs to be calculated on the fly
            registered_so_far = [v.content_model for v in self.versionables]
            if versionable.content_model in registered_so_far:
                raise ImproperlyConfigured(
                    "{!r} has already been registered".format(versionable.content_model)
                )
            # Checks passed. Add versionable to our master list
            self.versionables.append(versionable)

    def handle_versioning_add_to_confirmation_context_setting(self, cms_config):
        """
        Check versioning_add_to_confirmation_context has been correctly set
        and add it to the master dict if all is ok
        """
        add_to_context = cms_config.versioning_add_to_confirmation_context
        supported_keys = ["unpublish"]
        for key, value in add_to_context.items():
            if key not in supported_keys:
                raise ImproperlyConfigured(
                    "{!r} is not a supported dict key in the versioning_add_to_confirmation_context setting".format(
                        key
                    )
                )
            if key not in self.add_to_context:
                self.add_to_context[key] = collections.OrderedDict()
            self.add_to_context[key].update(value)

    def handle_admin_classes(self, cms_config):
        """Replaces admin model classes for all registered content types
        with an admin model class that inherits from `versionable.content_admin_mixin`.
        """
        replace_admin_for_models(
            [
                (versionable.content_model, versionable.content_admin_mixin)
                for versionable in cms_config.versioning
            ]
        )

    def handle_version_admin(self, cms_config):
        """
        Registers version admin for all registered content types
        with filtering by content type applied, so only versions for
        that specific content type are shown.
        """
        for versionable in cms_config.versioning:
            if versionable.concrete:
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
        # Validation to ensure either the versioning or the
        # versioning_add_to_confirmation_context config has been defined
        has_extra_context = hasattr(
            cms_config, "versioning_add_to_confirmation_context"
        )
        has_models_to_register = hasattr(cms_config, "versioning")
        if not has_extra_context and not has_models_to_register:
            raise ImproperlyConfigured(
                "The versioning or versioning_add_to_confirmation_context setting must be defined"
            )
        # No exception raised so now configure based on those settings
        if has_extra_context:
            self.handle_versioning_add_to_confirmation_context_setting(cms_config)
        if has_models_to_register:
            self.handle_versioning_setting(cms_config)
            self.handle_admin_classes(cms_config)
            self.handle_version_admin(cms_config)
            self.handle_content_model_generic_relation(cms_config)
            self.handle_content_model_manager(cms_config)


def copy_page_content(original_content):
    """Copy the PageContent object and deepcopy its
    placeholders and plugins.
    """
    # Copy content object
    content_fields = {
        field.name: getattr(original_content, field.name)
        for field in PageContent._meta.fields
        # Don't copy the pk as we're creating a new obj.
        # The creation date should reflect the date it was copied on,
        # so don't copy that either.
        if field.name not in (PageContent._meta.pk.name, "creation_date")
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
            if field.name not in [Placeholder._meta.pk.name, "source"]
        }
        if placeholder.source:
            placeholder_fields["source"] = new_content
        new_placeholder = Placeholder.objects.create(**placeholder_fields)
        # Copy plugins
        placeholder.copy_plugins(new_placeholder)
        new_placeholders.append(new_placeholder)
    new_content.placeholders.add(*new_placeholders)

    return new_content


def label_from_instance(obj, language):
    """
    Override the label for each grouper select option
    """
    title = obj.get_title(language) or _("No available title")
    path = obj.get_path(language)
    path = "/{}/".format(path) if path else _("Unpublished")
    return "{title} ({path})".format(title=title, path=path)


def on_page_content_publish(version):
    """Url path and cache operations to do when a PageContent obj is published"""
    page = version.content.page
    language = version.content.language
    page._update_url_path(language)
    if page.is_home:
        page._remove_title_root_path()
    page._update_url_path_recursive(language)
    page.clear_cache(menu=True)


def on_page_content_unpublish(version):
    """Url path and cache operations to do when a PageContent obj is unpublished"""
    page = version.content.page
    language = version.content.language
    page._update_url_path_recursive(language)
    page.clear_cache(menu=True)


def on_page_content_draft_create(version):
    """Clear cache when a new PageContent draft is created."""
    page = version.content.page
    page.clear_cache(menu=True)


def on_page_content_archive(version):
    """Clear cache when a new PageContent version is archived."""
    page = version.content.page
    page.clear_cache(menu=True)


class VersioningCMSPageAdminMixin(VersioningAdminMixin):
    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        if obj:
            version = Version.objects.get_for_content(obj)
            if not version.check_modify.as_bool(request.user):
                form = self.get_form_class(request)
                if getattr(form, "fieldsets"):
                    fields = flatten_fieldsets(form.fieldsets)
                fields = list(fields)
                for f_name in ["slug", "overwrite_url"]:
                    fields.remove(f_name)
        return fields

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj:
            version = Version.objects.get_for_content(obj)
            if not version.check_modify.as_bool(request.user):
                for f_name in ["slug", "overwrite_url"]:
                    form.declared_fields[f_name].widget.attrs["readonly"] = True
        return form


class VersioningCMSConfig(CMSAppConfig):
    """Implement versioning for core cms models
    """

    djangocms_versioning_enabled = getattr(
        settings, "VERSIONING_CMS_MODELS_ENABLED", True
    )
    versioning = [
        VersionableItem(
            content_model=PageContent,
            grouper_field_name="page",
            extra_grouping_fields=["language"],
            version_list_filter_lookups={"language": get_language_tuple},
            copy_function=copy_page_content,
            grouper_selector_option_label=label_from_instance,
            on_publish=on_page_content_publish,
            on_unpublish=on_page_content_unpublish,
            on_draft_create=on_page_content_draft_create,
            on_archive=on_page_content_archive,
            content_admin_mixin=VersioningCMSPageAdminMixin,
            admin_list_display_fields=["title"],
        )
    ]
