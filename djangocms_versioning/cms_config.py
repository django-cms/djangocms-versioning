import collections

from cms.app_base import CMSAppConfig, CMSAppExtension
from cms.extensions.models import BaseExtension
from cms.models import PageContent, Placeholder
from cms.utils import get_language_from_request
from cms.utils.i18n import get_language_list, get_language_tuple
from cms.utils.plugins import copy_plugins_to_placeholder
from cms.utils.urlutils import admin_reverse
from django.conf import settings
from django.contrib.admin.utils import flatten_fieldsets
from django.core.exceptions import (
    ImproperlyConfigured,
    ObjectDoesNotExist,
    PermissionDenied,
)
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
)
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from . import indicators, versionables
from .admin import VersioningAdminMixin
from .conf import LOCK_VERSIONS
from .constants import INDICATOR_DESCRIPTIONS
from .datastructures import BaseVersionableItem, VersionableItem
from .exceptions import ConditionFailed
from .helpers import (
    get_latest_admin_viewable_content,
    inject_generic_relation_to_version,
    placeholder_content_is_unlocked_for_user,
    register_versionadmin_proxy,
    replace_admin_for_models,
    replace_manager,
)
from .managers import AdminManagerMixin, PublishedContentManagerMixin
from .models import Version
from .plugin_rendering import CMSToolbarVersioningMixin


class VersioningCMSExtension(CMSAppExtension):
    def __init__(self):
        self.versionables = []
        self.add_to_context = {}
        self.add_to_field_extension = {}

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
                    f"{versionable!r} is not a subclass of djangocms_versioning.datastructures.BaseVersionableItem"
                )
            # NOTE: Do not use the cached property here as this is
            # still changing and needs to be calculated on the fly
            registered_so_far = [v.content_model for v in self.versionables]
            if versionable.content_model in registered_so_far:
                raise ImproperlyConfigured(
                    f"{versionable.content_model!r} has already been registered"
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
                    f"{key!r} is not a supported dict key in the versioning_add_to_confirmation_context setting"
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
            replace_manager(versionable.content_model, "objects", PublishedContentManagerMixin)
            replace_manager(versionable.content_model, "admin_manager", AdminManagerMixin,
                            _group_by_key=list(versionable.grouping_fields))

    def handle_admin_field_modifiers(self, cms_config):
        """Allows for the transformation of a given field in the ExtendedVersionAdminMixin
        """
        extended_admin_field_modifiers = getattr(cms_config, "extended_admin_field_modifiers", None)
        if not isinstance(extended_admin_field_modifiers, list):
            raise ImproperlyConfigured("extended_admin_field_modifiers must be list of dictionaries")
        for modifier in extended_admin_field_modifiers:
            for key in modifier.keys():
                self.add_to_field_extension[key] = modifier[key]

    def handle_locking(self):
        if LOCK_VERSIONS:
            from cms.models import fields

            fields.PlaceholderRelationField.default_checks += [placeholder_content_is_unlocked_for_user]

    def configure_app(self, cms_config):
        if hasattr(cms_config, "extended_admin_field_modifiers"):
            self.handle_admin_field_modifiers(cms_config)
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
        self.handle_locking()


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

    # Use original manager to not create a new Version object here
    new_content = PageContent._original_manager.create(**content_fields)

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

    # If pagecontent has an associated content or page extension, also copy this!
    for field in PageContent._meta.related_objects:
        if hasattr(original_content, field.name):
            extension = getattr(original_content, field.name)
            if isinstance(extension, BaseExtension):
                extension.copy(new_content, new_content.language)

    return new_content


def label_from_instance(obj, language):
    """
    Override the label for each grouper select option
    """
    title = obj.get_title(language) or _("No available title")
    path = obj.get_path(language)
    path = f"/{path}/" if path else _("Unpublished")
    return f"{title} ({path})"


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
                if form.fieldsets:
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

    def get_queryset(self, request):
        urls = ("cms_pagecontent_get_tree",)
        queryset = super().get_queryset(request)
        if request.resolver_match.url_name in urls:
            versionable = versionables.for_content(queryset.model)

            # TODO: Improve the grouping filters to use anything defined in the
            #       apps versioning config extra_grouping_fields
            grouping_filters = {}
            if "language" in versionable.extra_grouping_fields:
                grouping_filters["language"] = get_language_from_request(request)

            return queryset.filter(pk__in=versionable.distinct_groupers(**grouping_filters))
        return queryset

    # CAVEAT:
    #   - PageContent contains the template, this can differ for each language,
    #     it is assumed that templates would be the same when copying from one language to another
    # FIXME: The long term solution will require knowing:
    #           - why this view is an ajax call
    #           - where it should live going forwards (cms vs versioning)
    #           - A better way of making the feature extensible / modifiable for versioning
    def copy_language(self, request, object_id):
        target_language = request.POST.get("target_language")

        # CAVEAT: Avoiding self.get_object because it sets the page cache,
        #         We don't want a draft showing to a regular site visitor!
        #         source_page_content = self.get_object(request, object_id=object_id)
        source_page_content = PageContent._original_manager.get(pk=object_id)

        if source_page_content is None:
            raise self._get_404_exception(object_id)

        page = source_page_content.page

        if not target_language or target_language not in get_language_list(site_id=page.node.site_id):
            return HttpResponseBadRequest(force_str(_("Language must be set to a supported language!")))

        target_page_content = get_latest_admin_viewable_content(page, language=target_language)

        # First check that we are able to edit the target
        if not self.has_change_permission(request, obj=target_page_content):
            raise PermissionDenied

        for placeholder in source_page_content.get_placeholders():
            # Try and get a matching placeholder, only if it exists
            try:
                target = target_page_content.get_placeholders().get(slot=placeholder.slot)
            except ObjectDoesNotExist:
                continue

            plugins = placeholder.get_plugins_list(source_page_content.language)

            if not target.has_add_plugins_permission(request.user, plugins):
                return HttpResponseForbidden(force_str(_("You do not have permission to copy these plugins.")))
            copy_plugins_to_placeholder(plugins, target, language=target_language)
        return HttpResponse("ok")

    def change_innavigation(self, request, object_id):
        page_content = self.get_object(request, object_id=object_id)
        version = Version.objects.get_for_content(page_content)
        try:
            version.check_modify(request.user)
        except ConditionFailed as e:
            # Send error message
            return HttpResponseForbidden(force_str(e))
        return super().change_innavigation(request, object_id)

    @property
    def indicator_descriptions(self):
        """Publish indicator description to CMSPageAdmin"""
        return INDICATOR_DESCRIPTIONS

    @classmethod
    def get_indicator_menu(cls, request, page_content):
        """Get the indicator menu for PageContent object taking into account the
        currently available versions"""
        menu_template = "admin/cms/page/tree/indicator_menu.html"
        status = page_content.content_indicator()
        if not status or status == "empty":  # pragma: no cover
            return super().get_indicator_menu(request, page_content)
        versions = page_content._version  # Cache from .content_indicator()
        back = admin_reverse("cms_pagecontent_changelist") + f"?language={request.GET.get('language')}"
        menu = indicators.content_indicator_menu(request, status, versions, back=back)
        return menu_template if menu else "", menu


class VersioningCMSConfig(CMSAppConfig):
    """Implement versioning for core cms models
    """
    cms_enabled = True
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
        )
    ]
    cms_toolbar_mixin = CMSToolbarVersioningMixin
    PageContent.add_to_class("is_editable", indicators.is_editable)
    PageContent.add_to_class("content_indicator", indicators.content_indicator)
