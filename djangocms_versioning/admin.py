import json
import typing
import warnings
from collections import OrderedDict
from urllib.parse import urlparse

from cms.admin.utils import CONTENT_PREFIX, ChangeListActionsMixin, GrouperModelAdmin
from cms.models import PageContent
from cms.utils import get_language_from_request
from cms.utils.conf import get_cms_setting
from cms.utils.urlutils import add_url_parameters, static_with_version
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.utils import unquote
from django.contrib.admin.views.main import ChangeList
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.db import models
from django.db.models import OuterRef, Subquery
from django.db.models.functions import Cast, Lower
from django.forms import MediaDefiningClass
from django.http import (
    Http404,
    HttpRequest,
    HttpResponseForbidden,
    HttpResponseNotAllowed,
)
from django.shortcuts import redirect, render
from django.template.loader import render_to_string, select_template
from django.template.response import TemplateResponse
from django.urls import Resolver404, path, resolve, reverse
from django.utils.encoding import force_str
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from . import conf, versionables
from .constants import DRAFT, INDICATOR_DESCRIPTIONS, PUBLISHED, VERSION_STATES
from .emails import notify_version_author_version_unlocked
from .exceptions import ConditionFailed
from .forms import grouper_form_factory
from .helpers import (
    content_is_unlocked_for_user,
    create_version_lock,
    get_admin_url,
    get_editable_url,
    get_latest_admin_viewable_content,
    get_preview_url,
    proxy_model,
    remove_version_lock,
    version_is_locked,
    version_list_url,
)
from .indicators import content_indicator, content_indicator_menu
from .models import Version
from .versionables import _cms_extension


class VersioningChangeListMixin:
    """Mixin used for ChangeList classes of content models."""

    def get_queryset(self, request):
        """Limit the content model queryset to the latest versions only."""
        queryset = super().get_queryset(request)
        versionable = versionables.for_content(queryset.model)

        """Check if there is a method "self.get_<field>_from_request" for each extra grouping field.
         If so call it to retrieve the appropriate filter. If no method is found (except for "language")
         no filter is applied. For "language" the fallback is versioning's "get_language_frmo_request".

         Admins requiring extra grouping field beside "language" need to implement the "get_<field>_from_request"
         method themselves. A common way to select the field might be GET or POST parameters or user-related settings.
         """

        grouping_filters = {}
        for field in versionable.extra_grouping_fields:
            if hasattr(self.model_admin, f"get_{field}_from_request"):
                grouping_filters[field] = getattr(self.model_admin, f"get_{field}_from_request")(request)
            elif field == "language":
                grouping_filters[field] = get_language_from_request(request)
        return queryset.filter(pk__in=versionable.distinct_groupers(**grouping_filters))


def versioning_change_list_factory(base_changelist_cls):
    """Generate a ChangeList class to use for the content model"""
    return type(
        "Versioned" + base_changelist_cls.__name__,
        (VersioningChangeListMixin, base_changelist_cls),
        {}
    )


class VersioningAdminMixin:
    """Mixin providing versioning functionality to admin classes of
    content models.
    """

    def save_model(self, request, obj, form, change):
        """
        Overrides the save method to create a version object
        when a content object is created
        """
        super().save_model(request, obj, form, change)
        if not change:
            if isinstance(obj, PageContent):
                # FIXME disabled version creation for `cms.PageContent`
                # here, as it's already done in `cms.api.create_title`
                return
            # create a new version object and save it
            Version.objects.create(content=obj, created_by=request.user)

    def get_queryset(self, request):
        """Override manager so records not in published state can be displayed"""
        from .helpers import override_default_manager

        with override_default_manager(self.model, self.model._original_manager):
            queryset = super().get_queryset(request)
        return queryset

    def get_changelist(self, request, **kwargs):
        ChangeList = super().get_changelist(request, **kwargs)
        return versioning_change_list_factory(ChangeList)

    change_form_template = "djangocms_versioning/admin/mixin/change_form.html"

    def render_change_form(
        self, request, context, add=False, change=False, form_url="", obj=None
    ):
        """Add a link to the version table to the change form view"""
        if "versioning_fallback_change_form_template" not in context:
            context[
                "versioning_fallback_change_form_template"
            ] = super().change_form_template

        return super().render_change_form(request, context, add=add, change=change, form_url=form_url, obj=obj)

    def has_change_permission(self, request, obj=None):
        # Add additional version checks
        if obj:
            version = Version.objects.get_for_content(obj)
            permission = version.check_modify.as_bool(request.user)
            if conf.LOCK_VERSIONS and permission:
                permission = content_is_unlocked_for_user(obj, request.user)
            return permission

        return super().has_change_permission(request, obj)


class StateIndicatorMixin(metaclass=MediaDefiningClass):
    """Mixin to provide state_indicator column to the changelist view of a content model admin. Usage::

        class MyContentModelAdmin(StateIndicatorMixin, admin.ModelAdmin):
            list_display = [..., "state_indicator", ...]
    """
    class Media:
        # js for the context menu
        js = ("admin/js/jquery.init.js", "djangocms_versioning/js/indicators.js",)
        # css for indicators and context menu
        css = {
            "all": (static_with_version("cms/css/cms.pagetree.css"),),
        }

    indicator_column_label = _("State")

    @property
    def _extra_grouping_fields(self):
        try:
            return versionables.for_grouper(self.model).extra_grouping_fields
        except KeyError:
            return None

    def get_indicator_column(self, request):
        def indicator(obj):
            if self._extra_grouping_fields is not None:  # Grouper Model
                content_obj = get_latest_admin_viewable_content(obj, include_unpublished_archived=True, **{
                    field: getattr(self, field) for field in self._extra_grouping_fields
                })
            else:  # Content Model
                content_obj = obj
            status = content_indicator(content_obj)
            menu = content_indicator_menu(
                request,
                status,
                content_obj._version,
                back=request.path_info + "?" + request.GET.urlencode(),
            ) if status else None
            return render_to_string(
                "admin/djangocms_versioning/indicator.html",
                {
                    "state": status or "empty",
                    "description": INDICATOR_DESCRIPTIONS.get(status, _("Empty")),
                    "menu_template": "admin/cms/page/tree/indicator_menu.html",
                    "menu": json.dumps(render_to_string("admin/cms/page/tree/indicator_menu.html",
                                                        {"indicator_menu_items": menu})) if menu else None,
                }
            )
        indicator.short_description = self.indicator_column_label
        return indicator

    def state_indicator(self, obj):
        raise ValueError(
            'ModelAdmin.display_list contains "state_indicator" as a placeholder for status indicators. '
            'Status indicators, however, are not loaded. If you implement "get_list_display" make '
            "sure it calls super().get_list_display."
        )  # pragma: no cover

    def get_list_display(self, request):
        """Default behavior: replaces the text "state_indicator" by the indicator column"""
        if versionables.exists_for_content(self.model) or versionables.exists_for_grouper(self.model):
            return tuple(self.get_indicator_column(request) if item == "state_indicator" else item
                         for item in super().get_list_display(request))
        else:
            # remove "state_indicator" entry
            return tuple(item for item in super().get_list_display(request) if item != "state_indicator")


class ExtendedListDisplayMixin:
    """Implements the extend_list_display method at allows other packages to add fields to the list display
    of a verisoned object"""

    @property
    def _is_grouper_admin(self):
        return isinstance(self, GrouperModelAdmin)

    def _get_field_modifier(self, request, modifier_dict, field):
        method = modifier_dict[field]

        def get_field_modifier(obj):
            if self._is_grouper_admin:  # In a grouper admin?
                return method(self.get_content_obj(obj), field)
            else:
                return method(obj, field)

        get_field_modifier.short_description = field
        return get_field_modifier

    def extend_list_display(self, request, modifier_dict, list_display):
        list_display = [*list_display]
        for field in modifier_dict:
            if not callable(modifier_dict[field]):
                raise ImproperlyConfigured("Field provided must be callable")
            try:
                prefix = CONTENT_PREFIX if self._is_grouper_admin else ""
                field_modifier = self._get_field_modifier(request, modifier_dict, field)
                list_display[list_display.index(prefix + field)] = field_modifier
            except ValueError:
                raise ImproperlyConfigured("The target field does not exist in this context") from None
        return tuple(list_display)

    def get_list_display(self, request):
        # get configured list_display
        list_display = super().get_list_display(request)
        # Get the versioning extension
        extension = _cms_extension()
        if isinstance(self, GrouperModelAdmin):
            modifier_dict = extension.add_to_field_extension.get(self.content_model, None)
        else:
            modifier_dict = extension.add_to_field_extension.get(self.model, None)
        if modifier_dict:
            list_display = self.extend_list_display(request, modifier_dict, list_display)
        return list_display


class ExtendedGrouperVersionAdminMixin(ExtendedListDisplayMixin):
    """Mixin to provide state_indicator, author and changed date column to the changelist view of a
    grouper model admin. Usage::

        class MyContentModelAdmin(ExtendedGrouperVersionAdminMixin, cms.admin.utils.GrouperModelAdmin):
            list_display = [
                ...,
                "get_author",   # Adds the author column
                "get_modified_date",  # Adds the modified column
                "get_versioning_state",  # Adds the state (w/o interaction)
                ...]

        """
    def get_queryset(self, request: HttpRequest) -> models.QuerySet:
        """Annotates the username of the ``created_by`` field, the ``modified`` field (date time),
        and the ``state`` field of the version object to the grouper queryset."""
        grouper_content_type = versionables.for_grouper(self.model).content_types
        qs = super().get_queryset(request)
        versions = Version.objects.filter(object_id=OuterRef("pk"), content_type__in=grouper_content_type)
        contents = self.content_model.admin_manager.latest_content(
            **{self.grouper_field_name: OuterRef("pk"), **self.current_content_filters}
        ).annotate(
            content_created_by=Subquery(versions.values(f"created_by__{conf.USERNAME_FIELD}")[:1]),
            content_state=Subquery(versions.values("state")),
            content_modified=Subquery(versions.values("modified")[:1]),
        )
        qs = qs.annotate(
            content_created_by=Subquery(contents.values("content_created_by")[:1]),
            content_created_by_sort=Lower(Subquery(contents.values("content_created_by")[:1])),
            content_state=Subquery(contents.values("content_state")),
            # cast is necessary for mysql
            content_modified=Cast(Subquery(contents.values("content_modified")[:1]), models.DateTimeField()),
        )
        return qs

    @admin.display(
        description=_("State"),
        ordering="content_state",
    )
    def get_versioning_state(self, obj: models.Model) -> typing.Union[str, None]:
        """Returns verbose text of objects versioning state. This is a text column without user interaction.
        Typically, either ``get_versioning_state`` or ``state_indicator`` (provided by the
        :class:`~djangocms_versioning.admin.StateIndicatorMixin`) is used. The state indicator
        allows for user interaction.
        :param obj: Versioned grouper model instance annotated with its content state
        :return: description of state
        """
        return dict(VERSION_STATES).get(obj.content_state)

    @admin.display(
        description=_("Author"),
        ordering="content_created_by_sort",
    )
    def get_author(self, obj: models.Model) -> typing.Union[str, None]:
        """
        Return the author who created a version
        :param obj: Versioned grouper model instance annotated with its author username
        :return: Author username
        """
        return getattr(obj, "content_created_by", None)

    # This needs to target the annotation, or ordering will be alphabetically, with uppercase then lowercase

    @admin.display(
        description=_("Modified"),
        ordering="content_modified",
    )
    def get_modified_date(self, obj: models.Model) -> typing.Union[str, None]:
        """
        Get the last modified date of a version
        :param obj: Versioned grouper model instance annotated with its modified datetime
        :return: Modified Date
        """
        return getattr(obj, "content_modified", None)


class ExtendedVersionAdminMixin(
    ExtendedListDisplayMixin,
    ChangeListActionsMixin,
    VersioningAdminMixin,
    metaclass=MediaDefiningClass,
):
    """
    Extended VersionAdminMixin for common/generic versioning admin items

    CAVEAT: Ordered fields are implemented by this mixin, if custom ordering is added to any models that
    inherits this Mixin it will require accommodating/reimplementing this.
    """

    versioning_list_display = (
        "get_author",
        "get_modified_date",
        "get_versioning_state",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # Due to django admin ordering using unicode, to alphabetically order regardless of case, we must
        # annotate the queryset, with the usernames all lower case, and then order based on that!

        queryset = queryset.annotate(created_by_username_ordering=Lower(f"versions__created_by__{conf.USERNAME_FIELD}"))
        return queryset

    def get_version(self, obj):
        """
        Return the latest version of a given object
        :param obj: Versioned Content instance
        :return: Latest Version linked with content instance
        """
        return obj.versions.all()[0]

    @admin.display(
        description=_("State"),
        ordering="versions__state",
    )
    def get_versioning_state(self, obj):
        """
        Return the state of a given version
        """
        return self.get_version(obj).get_state_display()

    @admin.display(
        description=_("Author"),
        ordering="created_by_username_ordering",
    )
    def get_author(self, obj):
        """
        Return the author who created a version
        :param obj: Versioned content model Instance
        :return: Author
        """
        return self.get_version(obj).created_by

    # This needs to target the annotation, or ordering will be alphabetically, with uppercase then lowercase

    @admin.display(
        description=_("Modified"),
        ordering="versions__modified",
    )
    def get_modified_date(self, obj):
        """
        Get the last modified date of a version
        :param obj: Versioned content model Instance
        :return: Modified Date
        """
        return self.get_version(obj).modified

    def _get_preview_url(self, obj):
        """
        Return the preview method if available, otherwise return None
        :return: method or None
        """
        if hasattr(obj, "get_preview_url"):
            return obj.get_preview_url()
        else:
            return None

    def _get_preview_link(self, obj, request, disabled=False):
        """
        Return a user-friendly button for previewing the content model
        :param obj: Instance of versioned content model
        :param request: The request to admin menu
        :param disabled: Should the link be marked disabled?
        :return: Preview icon template
        """
        preview_url = self._get_preview_url(obj) or get_preview_url(obj)
        if not preview_url:
            disabled = True

        return self.admin_action_button(
            preview_url,
            icon="view",
            title=_("Preview"),
            name="preview",
            keepsideframe=False,
            disabled=disabled,
        )

    def _get_edit_link(self, obj, request, disabled=False):
        """
        Return a user-friendly button for editing the content model
        - mark disabled if user doesn't have permission
        - hide completely if instance cannot be edited
        :param obj: Instance of Versioned model
        :param request: The request to admin menu
        :param disabled: Should the link be marked disabled?
        :return: Preview icon template
        """
        version = proxy_model(self.get_version(obj), self.model)

        if not version.check_edit_redirect.as_bool(request.user):
            # Don't display the link if it can't be edited
            return ""

        if not request.user.has_perm(f"{obj._meta.app_label}.{obj._meta.model_name}"):
            # Grey out if user has not sufficient right to edit
            disabled = True

        url = reverse(
            f"admin:{version._meta.app_label}_{version._meta.model_name}_edit_redirect",
            args=(version.pk,),
        )
        return self.admin_action_button(
            url,
            icon="pencil",
            title=_("Edit"),
            name="edit",
            disabled=disabled,
            action="post",
            keepsideframe=False,
        )

    def _get_manage_versions_link(self, obj, request, disabled=False):
        url = version_list_url(obj)
        return self.admin_action_button(
            url,
            icon="copy",
            title=_("Manage versions"),
            name="manage-versions",
            disabled=disabled,
        )

    def get_actions_list(self):
        """
        Collect rendered actions from implemented methods and return as list
        """
        actions = [
            self._get_preview_link,
            self._get_edit_link,
         ]
        if "state_indicator" not in self.versioning_list_display:
            # State indicator mixin loaded?
            actions.append(self._get_manage_versions_link)
        return actions

    def get_list_display(self, request):
        # get configured list_display
        list_display = super().get_list_display(request)
        # Add versioning information and action fields
        list_display += self.versioning_list_display + (self.get_admin_list_actions(request),)
        return list_display


class ExtendedIndicatorVersionAdminMixin(StateIndicatorMixin, ExtendedVersionAdminMixin):
    versioning_list_display = (
        "get_author",
        "get_modified_date",
        "state_indicator",
    )


class VersionChangeList(ChangeList):
    def get_filters_params(self, params=None):
        """Removes the grouper param from the filters as the main grouper
        filtering is not handled by the UI filters and therefore needs to be
        handled differently.
        """
        content_model = self.model_admin.model._source_model
        versionable = versionables.for_content(content_model)
        filter_params = super().get_filters_params(params)
        filter_params.pop(versionable.grouper_field_name, None)
        return filter_params

    def get_grouping_field_filters(self, request):
        """Handles extra grouping params (such as PageContent.language).

        The get_filters_params method does return these filters as they are
        visible in the UI, however they need extra handling due to db
        optimization and the difficulties involved in handling the
        generic foreign key from Version to the content model."""
        content_model = self.model_admin.model._source_model
        versionable = versionables.for_content(content_model)
        fields = versionable.grouping_fields
        for field in fields:
            value = request.GET.get(field)
            if value is not None:
                yield field, value

    def get_queryset(self, request):
        """Adds support for querying the version model by grouping fields.

        Filters by the value of grouping fields (specified in VersionableItem
        definition) of content model.

        Functionality is implemented here, because list_filter doesn't allow
        for specifying filters that work without being shown in the UI
        along with filter choices.
        """
        queryset = super().get_queryset(request)
        content_model = self.model_admin.model._source_model
        versionable = versionables.for_content(content_model)
        filters = dict(self.get_grouping_field_filters(request))
        if versionable.grouper_field_name not in filters:
            raise IncorrectLookupParameters("Missing grouper")
        return queryset.filter_by_grouping_values(versionable, **filters)


def fake_filter_factory(versionable, field_name):
    """Returns filters that merely expose the filtering UI,
    without having any effect on the resulting queryset.
    """
    field = versionable.content_model._meta.get_field(field_name)
    lookups_ = versionable.version_list_filter_lookups[field_name]

    class FakeFilter(admin.SimpleListFilter):
        title = field.verbose_name
        parameter_name = field_name

        def lookups(self, request, model_admin):
            if callable(lookups_):
                return lookups_()
            else:
                return lookups_

        def queryset(self, request, queryset):
            return queryset

    return FakeFilter


class VersionAdmin(ChangeListActionsMixin, admin.ModelAdmin, metaclass=MediaDefiningClass):
    """Admin class used for version models.
    """

    # register custom actions
    actions = ["compare_versions"]
    list_display = (
        "number",
        "created",
        "modified",
        "content",
        "created_by",
    ) + (
        ("locked",) if conf.LOCK_VERSIONS else ()
    ) + (
        "state",
        "admin_list_actions",
    )
    list_display_links = None

    # FIXME disabled until GenericRelation attached to content models gets
    # fixed to include subclass (polymorphic) support
    #
    # def get_queryset(self, request):
    #     return super().get_queryset(request).prefetch_related('content')

    class Media:
        js = ["djangocms_versioning/js/versioning.js"]

    def get_changelist(self, request, **kwargs):
        return VersionChangeList

    def get_list_filter(self, request):
        """Adds the filters for the extra grouping fields to the UI."""
        versionable = versionables.for_content(self.model._source_model)
        return [
            fake_filter_factory(versionable, field)
            for field in versionable.extra_grouping_fields
        ]

    def get_actions(self, request):
        """Removes the standard django admin delete action."""
        actions = super().get_actions(request)
        # disable delete action
        if "delete_selected" in actions and not conf.ALLOW_DELETING_VERSIONS:
            del actions["delete_selected"]
        return actions

    @admin.display(
        description=_("Content"),
        ordering="content",
    )
    def content_link(self, obj):
        """Display html for the content preview url - replaced by Preview action"""
        warnings.warn("VersionAdmin.content_link is deprecated.", DeprecationWarning, stacklevel=2)
        content = obj.content
        url = get_preview_url(content)

        return format_html(
            '<a target="_top" class="js-close-sideframe" href="{url}">{label}</a>',
            url=mark_safe(url),
            label=content,
        )

    @admin.display(
        description=_("locked")
    )
    def locked(self, version):
        """
        Generate an locked field for Versioning Admin
        """
        if version.state == DRAFT and version_is_locked(version):
            return mark_safe('<span class="cms-icon cms-icon-lock"></span>')
        return ""

    def _get_preview_link(self, obj, request):
        if obj.state == DRAFT:
            # Draft versions have edit button
            return ""
        url = get_preview_url(obj.content)
        return self.admin_action_button(
            url,
            icon="view",
            name="preview",
            keepsideframe=False,
            title=_("Preview"),
        )

    def _get_archive_link(self, obj, request, disabled=False):
        """Helper function to get the html link to the archive action
        """
        if not obj.can_be_archived():
            # Don't display the link if it can't be archived
            return ""
        archive_url = reverse(
            f"admin:{obj._meta.app_label}_{self.model._meta.model_name}_archive",
            args=(obj.pk,),
        )
        return self.admin_action_button(
            archive_url,
            icon="archive",
            title=_("Archive"),
            name="archive",
            disabled=not obj.can_be_archived(),
        )

    def _get_publish_link(self, obj, request):
        """Helper function to get the html link to the publish action
        """
        if not obj.check_publish.as_bool(request.user):
            # Don't display the link if it can't be published
            return ""
        publish_url = reverse(
            f"admin:{obj._meta.app_label}_{self.model._meta.model_name}_publish",
            args=(obj.pk,),
        )
        return self.admin_action_button(
            publish_url,
            icon="publish",
            title=_("Publish"),
            name="publish",
            action="post",
            disabled=not obj.can_be_published(),
            keepsideframe=False,
        )

    def _get_unpublish_link(self, obj, request, disabled=False):
        """Helper function to get the html link to the unpublish action
        """
        if not obj.check_unpublish.as_bool(request.user):
            # Don't display the link if it can't be unpublished
            return ""
        unpublish_url = reverse(
            f"admin:{obj._meta.app_label}_{self.model._meta.model_name}_unpublish",
            args=(obj.pk,),
        )
        return self.admin_action_button(
            unpublish_url,
            icon="unpublish",
            title=_("Unpublish"),
            name="unpublish",
            disabled=not obj.can_be_unpublished(),
        )

    def _get_edit_link(self, obj, request, disabled=False):
        """Helper function to get the html link to the edit action
        """
        if not obj.check_edit_redirect.as_bool(request.user):
            return ""

        # Only show if no draft exists
        if obj.state == PUBLISHED:
            pks_for_grouper = obj.versionable.for_content_grouping_values(
                obj.content
            ).values_list("pk", flat=True)
            drafts = Version.objects.filter(
                object_id__in=pks_for_grouper,
                content_type=obj.content_type,
                state=DRAFT,
            )
            if drafts.exists():
                return ""
            icon = "edit-new"
        else:
            icon = "pencil"

        # Don't open in the sideframe if the item is not sideframe compatible
        keepsideframe = obj.versionable.content_model_is_sideframe_editable

        edit_url = reverse(
            f"admin:{obj._meta.app_label}_{self.model._meta.model_name}_edit_redirect",
            args=(obj.pk,),
        )
        return self.admin_action_button(
            edit_url,
            icon=icon,
            title=_("Edit") if icon == "pencil" else _("New Draft"),
            name="edit",
            action="post",
            disabled=disabled,
            keepsideframe=keepsideframe,
        )

    def _get_revert_link(self, obj, request, disabled=False):
        """Helper function to get the html link to the revert action
        """
        if not obj.check_revert.as_bool(request.user):
            # Don't display the link if it's a draft or published
            return ""

        revert_url = reverse(
            f"admin:{obj._meta.app_label}_{self.model._meta.model_name}_revert",
            args=(obj.pk,),
        )
        return self.admin_action_button(
            revert_url,
            icon="undo",
            title=_("Revert"),
            name="revert",
            disabled=disabled,
        )

    def _get_discard_link(self, obj, request, disabled=False):
        """Helper function to get the html link to the discard action
        """
        if not obj.check_discard.as_bool(request.user):
            # Don't display the link if it's not a draft
            return ""

        discard_url = reverse(
            f"admin:{obj._meta.app_label}_{self.model._meta.model_name}_discard",
            args=(obj.pk,),
        )
        return self.admin_action_button(
            discard_url,
            icon="bin",
            title=_("Discard"),
            name="discard",
            disabled=disabled,
        )

    def _get_unlock_link(self, obj, request):
        """
        Generate an unlock link for the Versioning Admin
        """
        # If the version is not draft no action should be present
        if not conf.LOCK_VERSIONS or obj.state != DRAFT or not version_is_locked(obj):
            return ""

        disabled = True
        # Check whether the lock can be removed
        # Check that the user has unlock permission
        if request.user.has_perm("djangocms_versioning.delete_versionlock"):
            disabled = False

        unlock_url = reverse(f"admin:{obj._meta.app_label}_{self.model._meta.model_name}_unlock", args=(obj.pk,))
        return self.admin_action_button(
            unlock_url,
            icon="unlock",
            title=_("Unlock"),
            name="unlock",
            action="post",
            disabled=disabled,
        )

    def get_actions_list(self):
        """Returns all action links as a list"""
        return self.get_state_actions()

    def get_state_actions(self):
        """Compatibility shim for djangocms-moderation. Do not use.
        It will be removed in a future version."""

        if settings.DEBUG:
            # Only introspect in DEBUG mode. Issue warning if method is monkey-patched
            import inspect
            caller_frame = inspect.getouterframes(inspect.currentframe(), 2)
            if caller_frame[1][3] != "get_actions_list":
                warnings.warn("Modifying get_state_actions is deprecated. VersionAdmin.get_state_actions "
                              "will be removed in a future version. Use get_actions_list instead.",
                              DeprecationWarning, stacklevel=2)

        return [
            self._get_preview_link,
            self._get_edit_link,
            self._get_archive_link,
            self._get_publish_link,
            self._get_unpublish_link,
            self._get_revert_link,
            self._get_discard_link,
            self._get_unlock_link,
        ]

    @admin.action(
        description=_("Compare versions")
    )
    def compare_versions(self, request, queryset):
        """
        Redirects to a compare versions view based on a users choice
        """
        queryset = queryset.order_by("pk")

        # Validate that only two versions are selected
        if queryset.count() != 2:
            self.message_user(request, _("Exactly two versions need to be selected."))
            return

        # Build the link for the version comparison of the two selected versions
        url = reverse(
            f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_compare",
            args=(queryset[0].pk,),
        )
        url += "?compare_to=%d" % queryset[1].pk

        return redirect(url)

    def grouper_form_view(self, request):
        """Displays an intermediary page to select a grouper object
        to show versions of.
        """
        language = get_language_from_request(request)
        context = dict(
            self.admin_site.each_context(request),
            opts=self.model._meta,
            form=grouper_form_factory(self.model._source_model, language)(),
        )
        return render(request, "djangocms_versioning/admin/grouper_form.html", context)

    def archive_view(self, request, object_id):
        """Archives the specified version and redirects back to the
        version changelist
        """

        # Check version exists
        version = self.get_object(request, unquote(object_id))
        if version is None:
            return self._get_obj_does_not_exist_redirect(
                request, self.model._meta, object_id
            )

        if not version.can_be_archived():
            self.message_user(request, _("Version cannot be archived"), messages.ERROR)
            return redirect(version_list_url(version.content))
        try:
            version.check_archive(request.user)
        except ConditionFailed as e:
            self.message_user(request, force_str(e), messages.ERROR)
            return redirect(version_list_url(version.content))

        if request.method != "POST":
            context = {
                "object_name": version.content,
                "version_number": version.number,
                "object_id": object_id,
                "archive_url": reverse(
                    f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_archive",
                    args=(version.content.pk,),
                ),
                "back_url": self.back_link(request, version),
            }
            return render(
                request, "djangocms_versioning/admin/archive_confirmation.html", context
            )
        else:
            # Archive the version
            version.archive(request.user)
            # Display message
            self.message_user(request, _("Version archived"))
        # Redirect
        return redirect(version_list_url(version.content))

    def publish_view(self, request, object_id):
        """Publishes the specified version and redirects back to the
        version changelist
        """
        # This view always changes data so only POST requests should work
        if request.method != "POST":
            return HttpResponseNotAllowed(
                ["POST"], _("This view only supports POST method.")
            )

        # Check version exists
        version = self.get_object(request, unquote(object_id))
        if version is None:
            return self._get_obj_does_not_exist_redirect(
                request, self.model._meta, object_id
            )

        if conf.ON_PUBLISH_REDIRECT in ("preview", "published"):
            redirect_url=get_preview_url(version.content)
        else:
            redirect_url=version_list_url(version.content)

        if not version.can_be_published():
            self.message_user(request, _("Version cannot be published"), messages.ERROR)
            return redirect(redirect_url)
        try:
            version.check_publish(request.user)
        except ConditionFailed as e:
            self.message_user(request, force_str(e), messages.ERROR)
            return redirect(redirect_url)

        # Publish the version
        version.publish(request.user)

        # Display message
        self.message_user(request, _("Version published"))

        # Redirect to published?
        if conf.ON_PUBLISH_REDIRECT == "published":
            redirect_url = None
            if hasattr(version.content, "get_absolute_url"):
                redirect_url = version.content.get_absolute_url() or redirect_url

        return redirect(redirect_url)

    def unpublish_view(self, request, object_id):
        """Unpublishes the specified version and redirects back to the
        version changelist
        """
        # Check version exists
        version = self.get_object(request, unquote(object_id))
        if version is None:
            return self._get_obj_does_not_exist_redirect(
                request, self.model._meta, object_id
            )

        if conf.ON_PUBLISH_REDIRECT in ("preview", "published"):
            redirect_url=get_preview_url(version.content)
        else:
            redirect_url=version_list_url(version.content)

        if not version.can_be_unpublished():
            self.message_user(
                request, _("Version cannot be unpublished"), messages.ERROR
            )
            return redirect(redirect_url)
        try:
            version.check_unpublish(request.user)
        except ConditionFailed as e:
            self.message_user(request, force_str(e), messages.ERROR)
            return redirect(redirect_url)

        if request.method != "POST":
            context = {
                "object_name": version.content,
                "version_number": version.number,
                "object_id": object_id,
                "unpublish_url": reverse(
                    f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_unpublish",
                    args=(version.content.pk,),
                ),
                "back_url": self.back_link(request, version),
            }
            extra_context = OrderedDict(
                [
                    (key, func(request, version))
                    for key, func in _cms_extension()
                    .add_to_context.get("unpublish", {})
                    .items()
                ]
            )
            context.update({"extra_context": extra_context})
            return render(
                request,
                "djangocms_versioning/admin/unpublish_confirmation.html",
                context,
            )
        else:
            # Unpublish the version
            version.unpublish(request.user)
            # Display message
            self.message_user(request, _("Version unpublished"))
        # Redirect
        return redirect(redirect_url)

    def _get_edit_redirect_version(self, request, version):
        """Helper method to get the latest draft or create one if one does not exist."""
        # If published then there's extra things to do...
        if version.state == PUBLISHED:
            # First check there is no draft record for this grouper
            # already.
            pks_for_grouper = version.versionable.for_content_grouping_values(
                version.content
            ).values_list("pk", flat=True)
            content_type = ContentType.objects.get_for_model(version.content)
            drafts = Version.objects.filter(
                object_id__in=pks_for_grouper, content_type=content_type, state=DRAFT
            )
            if drafts.exists():
                # There is a draft record so people should be editing
                # the draft record not the published one. Redirect to draft.
                draft = drafts.first()
                # Run edit checks for the found draft as well
                draft.check_edit_redirect(request.user)
                if conf.LOCK_VERSIONS:
                    create_version_lock(version, request.user)
                return draft
            # If there is no draft record then create a new version
            # that's a draft with the content copied over
            return version.copy(request.user)
        elif version.state == DRAFT:
            if conf.LOCK_VERSIONS:
                create_version_lock(version, request.user)
            # Return current version as it is a draft
            return version

    def edit_redirect_view(self, request, object_id):
        """Redirects to the admin change view and creates a draft version
        if no draft exists yet.
        """
        # This view always changes data so only POST requests should work
        if request.method != "POST":
            return HttpResponseNotAllowed(
                ["POST"], _("This view only supports POST method.")
            )

        version = self.get_object(request, unquote(object_id))
        if version is None:
            raise Http404

        try:
            version.check_edit_redirect(request.user)
            target = self._get_edit_redirect_version(request, version)
        except ConditionFailed as e:
            self.message_user(request, force_str(e), messages.ERROR)
            return redirect(version_list_url(version.content))

        # Redirect
        return redirect(get_editable_url(target.content))

    def revert_view(self, request, object_id):
        """Reverts to the specified version i.e. creates a draft from it."""
        version = self.get_object(request, unquote(object_id))

        if version is None:
            raise Http404

        try:
            version.check_revert(request.user)
        except ConditionFailed as e:
            self.message_user(request, force_str(e), messages.ERROR)
            return redirect(version_list_url(version.content))

        pks_for_grouper = version.versionable.for_content_grouping_values(
            version.content
        ).values_list("pk", flat=True)
        drafts = Version.objects.filter(
            object_id__in=pks_for_grouper,
            content_type=version.content_type,
            state=DRAFT,
        )

        draft_version = None
        if drafts.exists():
            draft_version = drafts.first()

        if request.method != "POST":
            context = {
                "object_name": version.content,
                "version_number": version.number,
                "draft_version": draft_version,
                "object_id": object_id,
                "revert_url": reverse(
                    f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_revert",
                    args=(version.content.pk,),
                ),
                "back_url": self.back_link(request, version),
            }
            return render(
                request, "djangocms_versioning/admin/revert_confirmation.html", context
            )
        else:

            if draft_version and request.POST.get("archive"):
                draft_version.archive(request.user)

            if draft_version and request.POST.get("discard"):
                draft_version.delete()

            version = version.copy(request.user)
            # Redirect
            return redirect(version_list_url(version.content))

    def discard_view(self, request, object_id):
        """Discards the specified version"""
        version = self.get_object(request, unquote(object_id))
        if version is None:
            raise Http404

        try:
            version.check_discard(request.user)
        except ConditionFailed as e:
            self.message_user(request, force_str(e), messages.ERROR)
            return redirect(version_list_url(version.content))

        if request.method != "POST":
            context = {
                "object_name": version.content,
                "version_number": version.number,
                "draft_version": version,
                "object_id": object_id,
                "revert_url": reverse(
                    f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_revert",
                    args=(version.content.pk,),
                ),
                "back_url": self.back_link(request, version),
            }
            return render(
                request, "djangocms_versioning/admin/discard_confirmation.html", context
            )

        version_url = version_list_url(version.content)
        if request.POST.get("discard"):
            ModelClass = version.content.__class__
            deleted = version.delete()
            if deleted[1]["last"]:
                version_url = get_admin_url(ModelClass, "changelist")
                self.message_user(request, _("The last version has been deleted"))

        return redirect(version_url)

    def compare_view(self, request, object_id):
        """Compares two versions
        """
        # Get version 1 (the version we're comparing against)
        v1 = self.get_object(request, unquote(object_id))
        if v1 is None:
            return self._get_obj_does_not_exist_redirect(
                request, self.model._meta, object_id
            )
        persist_params = {
            get_cms_setting("CMS_TOOLBAR_URL__DISABLE"): 1,
            get_cms_setting("CMS_TOOLBAR_URL__PERSIST"): 0,
        }
        v1_preview_url = get_preview_url(v1.content)
        v1_preview_url = add_url_parameters(v1_preview_url, **persist_params)
        # Get the list of versions for the grouper. This is for use
        # in the dropdown to choose a version.
        version_list = Version.objects.filter_by_content_grouping_values(
            v1.content
        ).order_by("-number")
        # Add the above to context
        context = {
            "version_list": version_list,
            "v1": v1,
            "v1_preview_url": v1_preview_url,
            "return_url": self.back_link(request, v1),
        }

        # Now check if version 2 has been specified and add to context
        # if yes
        if "compare_to" in request.GET:
            v2 = self.get_object(request, unquote(request.GET["compare_to"]))
            if v2 is None:
                return self._get_obj_does_not_exist_redirect(
                    request, self.model._meta, request.GET["compare_to"]
                )
            else:
                v2_preview_url = get_preview_url(v2.content)
                context.update(
                    {
                        "v2": v2,
                        "v2_preview_url": add_url_parameters(v2_preview_url, **persist_params),
                    }
                )
        return TemplateResponse(
            request, "djangocms_versioning/admin/compare.html", context
        )

    def unlock_view(self, request, object_id):
        """
        Unlock a locked version
        """
        # Only active if LOCK_VERISONS is set
        if not conf.LOCK_VERSIONS:
            raise Http404()

        # This view always changes data so only POST requests should work
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"], _("This view only supports POST method."))

        # Check version exists
        version = self.get_object(request, unquote(object_id))
        if version is None:
            return self._get_obj_does_not_exist_redirect(
                request, self.model._meta, object_id)

        # Raise 404 if not locked
        if version.state != DRAFT:
            raise Http404

        # Check that the user has unlock permission
        if not request.user.has_perm("djangocms_versioning.delete_versionlock"):
            return HttpResponseForbidden(force_str(_("You do not have permission to remove the version lock")))

        # Unlock the version
        remove_version_lock(version)
        # Display message
        messages.success(request, _("Version unlocked"))

        # Send an email notification
        notify_version_author_version_unlocked(version, request.user)

        # Redirect
        url = version_list_url(version.content)
        return redirect(url)

    @staticmethod
    def back_link(request, version=None):
        back_url = request.GET.get("back", None)
        if back_url:
            try:
                # Is return url a valid url?
                resolve(urlparse(back_url)[2])
            except Resolver404:
                # If not ignore
                back_url = None
        return back_url or (version_list_url(version.content) if version else None)

    def changelist_view(self, request, extra_context=None):
        """Handle grouper filtering on the changelist"""
        if not request.GET:
            # redirect to grouper form when there's no GET parameters
            opts = self.model._meta
            return redirect(
                reverse(f"admin:{opts.app_label}_{opts.model_name}_grouper")
            )
        extra_context = extra_context or {}
        versionable = versionables.for_content(self.model._source_model)

        try:
            grouper = versionable.get_grouper_with_fallbacks(
                int(request.GET.get(versionable.grouper_field_name))
            )
        except (TypeError, ValueError):
            grouper = None
        else:
            if grouper is None:
                # no exception and no grouper, thus the querydict is invalid
                raise Http404

        if grouper:
            # CAVEAT: as the breadcrumb trails expect a value for latest content in the template
            extra_context["latest_content"] = ({"pk": None})

            extra_context.update(
                grouper=grouper,
                title=_('Displaying versions of "{grouper}"').format(grouper=grouper),
            )
            breadcrumb_opts = self.model._source_model._meta
            extra_context["breadcrumb_opts"] = breadcrumb_opts
            # Check if custom breadcrumb template defined, otherwise
            # fallback on default
            breadcrumb_templates = [
                "admin/djangocms_versioning/{app_label}/{model_name}/versioning_breadcrumbs.html".format(
                    app_label=breadcrumb_opts.app_label,
                    model_name=breadcrumb_opts.model_name,
                ),
                "admin/djangocms_versioning/versioning_breadcrumbs.html",
            ]
            extra_context["breadcrumb_template"] = select_template(breadcrumb_templates)

        response = super().changelist_view(request, extra_context)

        # This is a slightly hacky way of accessing the instance of
        # the changelist that the admin changelist_view instantiates.
        # We do this to make sure that the latest content object is
        # picked from the same queryset as is being displayed in the
        # version table.
        if grouper and response.status_code == 200:
            # Catch the edge case where a grouper can have empty contents
            # when additional filters are present and the result set will be
            # empty for the additional values.
            try:
                response.context_data["latest_content"] = (
                    response.context_data["cl"].get_queryset(request)
                        .latest("created")
                        .content
                )
            except ObjectDoesNotExist:
                pass
        return response

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        return [
            path(
                "select/",
                self.admin_site.admin_view(self.grouper_form_view),
                name="{}_{}_grouper".format(*info),
            ),
            path(
                "<path:object_id>/archive/",
                self.admin_site.admin_view(self.archive_view),
                name="{}_{}_archive".format(*info),
            ),
            path(
                r"<path:object_id>/publish/",
                self.admin_site.admin_view(self.publish_view),
                name="{}_{}_publish".format(*info),
            ),
            path(
                "<path:object_id>/unpublish/",
                self.admin_site.admin_view(self.unpublish_view),
                name="{}_{}_unpublish".format(*info),
            ),
            path(
                "<path:object_id>/edit-redirect/",
                self.admin_site.admin_view(self.edit_redirect_view),
                name="{}_{}_edit_redirect".format(*info),
            ),
            path(
                "<path:object_id>/revert/",
                self.admin_site.admin_view(self.revert_view),
                name="{}_{}_revert".format(*info),
            ),
            path(
                "<path:object_id>/compare/",
                self.admin_site.admin_view(self.compare_view),
                name="{}_{}_compare".format(*info),
            ),
            path(
                "<path:object_id>/discard/",
                self.admin_site.admin_view(self.discard_view),
                name="{}_{}_discard".format(*info),
            ),
            path(
                "<path:object_id>/unlock/",
                self.admin_site.admin_view(self.unlock_view),
                name="{}_{}_unlock".format(*info),
            ),
        ] + super().get_urls()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        """Disable change view access"""
        if obj is not None:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False
