from collections import OrderedDict

from django.contrib import admin, messages
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.utils import unquote
from django.contrib.admin.views.main import ChangeList
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.template.loader import render_to_string, select_template
from django.template.response import TemplateResponse
from django.urls import re_path, reverse
from django.utils.encoding import force_str
from django.utils.formats import localize
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _

from cms.models import PageContent
from cms.utils import get_language_from_request
from cms.utils.conf import get_cms_setting
from cms.utils.urlutils import add_url_parameters

from . import versionables
from .constants import ARCHIVED, DRAFT, PUBLISHED, UNPUBLISHED
from .exceptions import ConditionFailed
from .forms import grouper_form_factory
from .helpers import (
    get_admin_url,
    get_editable_url,
    get_preview_url,
    proxy_model,
    version_list_url,
)
from .models import Version
from .versionables import _cms_extension


class VersioningChangeListMixin:
    """Mixin used for ChangeList classes of content models."""

    def get_queryset(self, request):
        """Limit the content model queryset to latest versions only."""
        queryset = super().get_queryset(request)
        versionable = versionables.for_content(queryset.model)

        # TODO: Improve the grouping filters to use anything defined in the
        #       apps versioning config extra_grouping_fields
        grouping_filters = {}
        if 'language' in versionable.extra_grouping_fields:
            grouping_filters['language'] = get_language_from_request(request)

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

        return super().render_change_form(request, context, add, change, form_url, obj)

    def has_change_permission(self, request, obj=None):
        # Add additional version checks
        if obj:
            version = Version.objects.get_for_content(obj)
            return version.check_modify.as_bool(request.user)
        return super().has_change_permission(request, obj)


class ExtendedVersionAdminMixin(VersioningAdminMixin):
    """
    Extended VersionAdminMixin for common/generic versioning admin items

    CAVEAT: Ordered fields are implemented by this mixin, if custom ordering is added to any models that
    inherits this Mixin it will require accommodating/reimplementing this.
    """

    change_list_template = "djangocms_versioning/admin/mixin/change_list.html"

    class Media:
        js = ("admin/js/jquery.init.js", "djangocms_versioning/js/actions.js")
        css = {
            "all": (
                "djangocms_versioning/css/actions.css",
            )
        }

    def get_version(self, obj):
        """
        Return the latest version of a given object
        :param obj: Versioned Content instance
        :return: Latest Version linked with content instance
        """
        return obj.versions.all()[0]

    def get_versioning_state(self, obj):
        """
        Return the state of a given version
        """
        return self.get_version(obj).get_state_display()

    get_versioning_state.admin_order_field = "versions__state"
    get_versioning_state.short_description = _("State")

    def get_author(self, obj):
        """
        Return the author who created a version
        :param obj: Versioned content model Instance
        :return: Author
        """
        return self.get_version(obj).created_by

    get_author.admin_order_field = "versions__created_by"
    get_author.short_description = _("Author")

    def get_modified_date(self, obj):
        """
        Get the last modified date of a version
        :param obj: Versioned content model Instance
        :return: Modified Date
        """
        return self.get_version(obj).modified

    get_modified_date.admin_order_field = "versions__modified"
    get_modified_date.short_description = _("Modified")

    def _get_preview_url(self, obj):
        """
        Return the preview method if available, otherwise return None
        :return: method or None
        """
        if hasattr(obj, "get_preview_url"):
            return obj.get_preview_url()
        else:
            return None

    def _get_published_url(self, obj):
        """
        Return the published url method if available, otherwise return None
        :return: method or None
        """
        try:
            return obj.content.get_absolute_url()
        except AttributeError:
            return None

    def _list_actions(self, request):
        """
        A closure that makes it possible to pass request object to
        list action button functions.
        """

        def list_actions(obj):
            """Display links to state change endpoints
            """
            return format_html_join(
                "",
                "{}",
                ((action(obj, request),) for action in self.get_list_actions()),
            )

        list_actions.short_description = _("actions")
        return list_actions

    def _get_preview_link(self, obj, request, disabled=False):
        """
        Return a user-friendly button for previewing the content model
        :param obj: Instance of versioned content model
        :param request: The request to admin menu
        :param disabled: Should the link be marked disabled?
        :return: Preview icon template
        """
        preview_url = self._get_preview_url(obj)
        if not preview_url:
            disabled = True

        return render_to_string(
            "djangocms_versioning/admin/icons/preview.html",
            {"url": preview_url or get_preview_url(obj), "disabled": disabled},
        )

    def _get_published_link(self, obj, request):
        """
        Return a user-friendly button for viewing the published content
        :param obj: Instance of versioned content model
        :param request: The request to admin menu
        :return: Published link icon template
        """
        published_url = self._get_published_url(obj)

        if not published_url:
            return ""

        return render_to_string(
            "djangocms_versioning/admin/icons/published_icon.html",
            {"published_url": published_url},
        )

    def _get_edit_link(self, obj, request, disabled=False):
        """
        Return a user friendly button for editing the content model
        - mark disabled if user doesn't have permission
        - hide completely if instance cannot be edited
        :param obj: Instance of Versioned model
        :param request: The request to admin menu
        :param disabled: Should the link be marked disabled?
        :return: Preview icon template
        """
        version = proxy_model(self.get_version(obj), self.model)

        if version.state not in (DRAFT, PUBLISHED):
            # Don't display the link if it can't be edited
            return ""

        if not version.check_edit_redirect.as_bool(request.user):
            disabled = True

        url = reverse(
            "admin:{app}_{model}_edit_redirect".format(
                app=version._meta.app_label, model=version._meta.model_name
            ),
            args=(version.pk,),
        )
        return render_to_string(
            "djangocms_versioning/admin/icons/edit_icon.html",
            {"url": url, "disabled": disabled, "get": False},
        )

    def _get_manage_versions_link(self, obj, request, disabled=False):
        url = version_list_url(obj)
        return render_to_string(
            "djangocms_versioning/admin/icons/manage_versions.html",
            {"url": url, "disabled": disabled, "action": False},
        )

    def get_list_actions(self):
        """
        Collect rendered actions from implemented methods and return as list
        """
        return [
            self._get_preview_link,
            self._get_edit_link,
            self._get_published_link,
            self._get_manage_versions_link,
        ]

    def get_preview_link(self, obj):
        return format_html(
            '<a href="{}" class="js-moderation-close-sideframe" target="_top">'
            '<span class="cms-icon cms-icon-eye"></span> {}'
            "</a>",
            obj.get_preview_url(),
            _("Preview"),
        )

    get_preview_link.short_description = _("Preview")

    def get_list_display(self, request):
        # get configured list_display
        list_display = self.list_display
        # Add versioning information and action fields
        list_display += (
            "get_author",
            "get_modified_date",
            "get_versioning_state",
            self._list_actions(request)
        )
        return list_display


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


class VersionAdmin(admin.ModelAdmin):
    """Admin class used for version models.
    """

    class Media:
        js = ("admin/js/jquery.init.js", "djangocms_versioning/js/actions.js", "djangocms_versioning/js/compare.js",)
        css = {"all": ("djangocms_versioning/css/actions.css",)}

    # register custom actions
    actions = ["compare_versions"]

    list_display_links = None

    # FIXME disabled until GenericRelation attached to content models gets
    # fixed to include subclass (polymorphic) support
    #
    # def get_queryset(self, request):
    #     return super().get_queryset(request).prefetch_related('content')

    def get_changelist(self, request, **kwargs):
        return VersionChangeList

    def get_list_filter(self, request):
        """Adds the filters for the extra grouping fields to the UI."""
        versionable = versionables.for_content(self.model._source_model)
        return [
            fake_filter_factory(versionable, field)
            for field in versionable.extra_grouping_fields
        ]

    def _state_actions(self, request):
        def state_actions(obj):
            """Display links to state change endpoints
            """
            return format_html_join(
                "",
                "{}",
                ((action(obj, request),) for action in self.get_state_actions()),
            )

        state_actions.short_description = _("actions")
        return state_actions

    def get_list_display(self, request):
        return (
            "nr",
            "created",
            "modified",
            "content_link",
            "created_by",
            "state",
            self._state_actions(request),
        )

    def get_actions(self, request):
        """Removes the standard django admin delete action."""
        actions = super().get_actions(request)
        # disable delete action
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions

    def nr(self, obj):
        """Get the identifier of the version. Might be something other
        than the pk eventually.
        """
        return obj.number

    nr.admin_order_field = "pk"
    nr.short_description = _("version number")

    def content_link(self, obj):
        """Display html for the content preview url"""
        content = obj.content
        url = get_preview_url(content)

        return format_html(
            '<a target="_top" class="js-versioning-close-sideframe" href="{url}">{label}</a>',
            url=url,
            label=content,
        )

    content_link.short_description = _("Content")
    content_link.admin_order_field = "content"

    def _get_archive_link(self, obj, request, disabled=False):
        """Helper function to get the html link to the archive action
        """
        if not obj.state == DRAFT:
            # Don't display the link if it can't be archived
            return ""
        archive_url = reverse(
            "admin:{app}_{model}_archive".format(
                app=obj._meta.app_label, model=self.model._meta.model_name
            ),
            args=(obj.pk,),
        )

        if not obj.can_be_archived() or not obj.check_archive.as_bool(request.user):
            disabled = True

        return render_to_string(
            "djangocms_versioning/admin/archive_icon.html",
            {"archive_url": archive_url, "disabled": disabled},
        )

    def _get_publish_link(self, obj, request):
        """Helper function to get the html link to the publish action
        """
        if not obj.state == DRAFT:
            # Don't display the link if it can't be published
            return ""
        publish_url = reverse(
            "admin:{app}_{model}_publish".format(
                app=obj._meta.app_label, model=self.model._meta.model_name
            ),
            args=(obj.pk,),
        )
        return render_to_string(
            "djangocms_versioning/admin/publish_icon.html", {"publish_url": publish_url}
        )

    def _get_unpublish_link(self, obj, request, disabled=False):
        """Helper function to get the html link to the unpublish action
        """
        if not obj.state == PUBLISHED:
            # Don't display the link if it can't be unpublished
            return ""
        unpublish_url = reverse(
            "admin:{app}_{model}_unpublish".format(
                app=obj._meta.app_label, model=self.model._meta.model_name
            ),
            args=(obj.pk,),
        )

        if not obj.can_be_unpublished() or not obj.check_unpublish.as_bool(
            request.user
        ):
            disabled = True

        return render_to_string(
            "djangocms_versioning/admin/unpublish_icon.html",
            {"unpublish_url": unpublish_url, "disabled": disabled},
        )

    def _get_published_link(self, obj, request):
        """Helper function to get the html link to the published page"""
        if not obj.state == PUBLISHED:
            # Don't display the link if it isn't published
            return ""

        published_url = obj.content.get_absolute_url()

        return render_to_string(
            "djangocms_versioning/admin/published_icon.html",
            {"published_url": published_url},
        )

    def _get_edit_link(self, obj, request, disabled=False):
        """Helper function to get the html link to the edit action
        """
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
        elif obj.state != DRAFT:
            # Don't display the link if it's not a draft
            return ""

        if not obj.check_edit_redirect.as_bool(request.user):
            disabled = True

        edit_url = reverse(
            "admin:{app}_{model}_edit_redirect".format(
                app=obj._meta.app_label, model=self.model._meta.model_name
            ),
            args=(obj.pk,),
        )
        return render_to_string(
            "djangocms_versioning/admin/edit_icon.html",
            {"edit_url": edit_url, "disabled": disabled},
        )

    def _get_revert_link(self, obj, request, disabled=False):
        """Helper function to get the html link to the revert action
        """
        if obj.state not in (UNPUBLISHED, ARCHIVED):
            # Don't display the link if it's a draft or published
            return ""

        revert_url = reverse(
            "admin:{app}_{model}_revert".format(
                app=obj._meta.app_label, model=self.model._meta.model_name
            ),
            args=(obj.pk,),
        )

        if not obj.check_revert.as_bool(request.user):
            disabled = True

        return render_to_string(
            "djangocms_versioning/admin/revert_icon.html",
            {"revert_url": revert_url, "disabled": disabled},
        )

    def _get_discard_link(self, obj, request, disabled=False):
        """Helper function to get the html link to the discard action
        """
        if obj.state not in (DRAFT,):
            # Don't display the link if it's not a draft
            return ""

        discard_url = reverse(
            "admin:{app}_{model}_discard".format(
                app=obj._meta.app_label, model=self.model._meta.model_name
            ),
            args=(obj.pk,),
        )

        if not obj.check_discard.as_bool(request.user):
            disabled = True

        return render_to_string(
            "djangocms_versioning/admin/discard_icon.html",
            {"discard_url": discard_url, "disabled": disabled},
        )

    def get_state_actions(self):
        """Returns all action links as a list"""
        return [
            self._get_edit_link,
            self._get_archive_link,
            self._get_publish_link,
            self._get_unpublish_link,
            self._get_published_link,
            self._get_revert_link,
            self._get_discard_link,
        ]

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
            "admin:{app}_{model}_compare".format(
                app=self.model._meta.app_label, model=self.model._meta.model_name
            ),
            args=(queryset[0].pk,),
        )
        url += "?compare_to=%d" % queryset[1].pk

        return redirect(url)

    compare_versions.short_description = _("Compare versions")

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
            context = dict(
                object_name=version.content,
                version_number=version.number,
                object_id=object_id,
                archive_url=reverse(
                    "admin:{app}_{model}_archive".format(
                        app=self.model._meta.app_label,
                        model=self.model._meta.model_name,
                    ),
                    args=(version.content.pk,),
                ),
                back_url=version_list_url(version.content),
            )
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

        if not version.can_be_published():
            self.message_user(request, _("Version cannot be published"), messages.ERROR)
            return redirect(version_list_url(version.content))
        try:
            version.check_publish(request.user)
        except ConditionFailed as e:
            self.message_user(request, force_str(e), messages.ERROR)
            return redirect(version_list_url(version.content))

        # Publish the version
        version.publish(request.user)
        # Display message
        self.message_user(request, _("Version published"))
        # Redirect
        return redirect(version_list_url(version.content))

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

        if not version.can_be_unpublished():
            self.message_user(
                request, _("Version cannot be unpublished"), messages.ERROR
            )
            return redirect(version_list_url(version.content))
        try:
            version.check_unpublish(request.user)
        except ConditionFailed as e:
            self.message_user(request, force_str(e), messages.ERROR)
            return redirect(version_list_url(version.content))

        if request.method != "POST":
            context = dict(
                object_name=version.content,
                version_number=version.number,
                object_id=object_id,
                unpublish_url=reverse(
                    "admin:{app}_{model}_unpublish".format(
                        app=self.model._meta.app_label,
                        model=self.model._meta.model_name,
                    ),
                    args=(version.content.pk,),
                ),
                back_url=version_list_url(version.content),
            )
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
        return redirect(version_list_url(version.content))

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
                return draft
            # If there is no draft record then create a new version
            # that's a draft with the content copied over
            return version.copy(request.user)
        elif version.state == DRAFT:
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
            context = dict(
                object_name=version.content,
                version_number=version.number,
                draft_version=draft_version,
                object_id=object_id,
                revert_url=reverse(
                    "admin:{app}_{model}_revert".format(
                        app=self.model._meta.app_label,
                        model=self.model._meta.model_name,
                    ),
                    args=(version.content.pk,),
                ),
                back_url=version_list_url(version.content),
            )
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
            context = dict(
                object_name=version.content,
                version_number=version.number,
                draft_version=version,
                object_id=object_id,
                revert_url=reverse(
                    "admin:{app}_{model}_revert".format(
                        app=self.model._meta.app_label,
                        model=self.model._meta.model_name,
                    ),
                    args=(version.content.pk,),
                ),
                back_url=version_list_url(version.content),
            )
            return render(
                request, "djangocms_versioning/admin/discard_confirmation.html", context
            )

        version_url = version_list_url(version.content)
        if request.POST.get("discard"):
            ModelClass = version.content.__class__
            deleted = version.delete()
            if deleted[1]['last']:
                version_url = get_admin_url(ModelClass, 'changelist')
                self.message_user(request, _('The last version has been deleted'))

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
        v1_preview_url = add_url_parameters(
            reverse(
                "admin:cms_placeholder_render_object_preview",
                args=(v1.content_type_id, v1.object_id),
            ),
            **persist_params
        )
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
            "v1_description": format_html(
                'Version #{number} ({date})',
                obj=v1,
                number=v1.number,
                date=localize(v1.created),
            ),
            "return_url": version_list_url(v1.content),
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
                context.update(
                    {
                        "v2": v2,
                        "v2_preview_url": add_url_parameters(
                            reverse(
                                "admin:cms_placeholder_render_object_preview",
                                args=(v2.content_type_id, v2.object_id),
                            ),
                            **persist_params
                        ),
                        "v2_description": format_html(
                            'Version #{number} ({date})',
                            obj=v2,
                            number=v2.number,
                            date=localize(v2.created),
                        ),
                    }
                )
        return TemplateResponse(
            request, "djangocms_versioning/admin/compare.html", context
        )

    def changelist_view(self, request, extra_context=None):
        """Handle grouper filtering on the changelist"""
        if not request.GET:
            # redirect to grouper form when there's no GET parameters
            opts = self.model._meta
            return redirect(
                reverse("admin:{}_{}_grouper".format(opts.app_label, opts.model_name))
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
            extra_context["latest_content"] = ({'pk': None})

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
            re_path(
                r"^select/$",
                self.admin_site.admin_view(self.grouper_form_view),
                name="{}_{}_grouper".format(*info),
            ),
            re_path(
                r"^(.+)/archive/$",
                self.admin_site.admin_view(self.archive_view),
                name="{}_{}_archive".format(*info),
            ),
            re_path(
                r"^(.+)/publish/$",
                self.admin_site.admin_view(self.publish_view),
                name="{}_{}_publish".format(*info),
            ),
            re_path(
                r"^(.+)/unpublish/$",
                self.admin_site.admin_view(self.unpublish_view),
                name="{}_{}_unpublish".format(*info),
            ),
            re_path(
                r"^(.+)/edit-redirect/$",
                self.admin_site.admin_view(self.edit_redirect_view),
                name="{}_{}_edit_redirect".format(*info),
            ),
            re_path(
                r"^(.+)/revert/$",
                self.admin_site.admin_view(self.revert_view),
                name="{}_{}_revert".format(*info),
            ),
            re_path(
                r"^(.+)/compare/$",
                self.admin_site.admin_view(self.compare_view),
                name="{}_{}_compare".format(*info),
            ),
            re_path(
                r"^(.+)/discard/$",
                self.admin_site.admin_view(self.discard_view),
                name="{}_{}_discard".format(*info),
            ),
        ] + super().get_urls()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        """Disable change view access
        """
        if obj is not None:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False
