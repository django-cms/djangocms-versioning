from django.apps import apps
from django.conf.urls import url
from django.contrib import admin, messages
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.views.main import ChangeList
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from .constants import DRAFT
from .forms import grouper_form_factory
from .models import Version


GROUPER_PARAM = 'grouper'


class VersioningAdminMixin:
    """Mixin providing versioning functionality to admin classes.
    """
    def save_model(self, request, obj, form, change):
        """
        Overrides the save method to create a version object
        when a content object is created
        """
        super().save_model(request, obj, form, change)
        if not change:
            # create a new version object and save it
            Version.objects.create(content=obj, created_by=request.user)

    def get_queryset(self, request):
        """Limit query to most recent content versions
        """
        queryset = super().get_queryset(request)
        versioning_extension = apps.get_app_config('djangocms_versioning').cms_extension
        versionable = versioning_extension.versionables_by_content[queryset.model]
        return queryset.filter(pk__in=versionable.distinct_groupers())


class VersionChangeList(ChangeList):

    def get_filters_params(self, params=None):
        lookup_params = super().get_filters_params(params)
        lookup_params.pop(GROUPER_PARAM, None)
        return lookup_params

    def get_queryset(self, request):
        """Adds support for querying the version model by content grouper
        field using ?grouper={id}.

        Filters by the value of grouper field (specified in VersionableItem
        definition) of content model.

        Functionality is implemented here, because list_filter doesn't allow
        for specifying filters that work without being shown in the UI
        along with filter choices.
        """
        qs = super().get_queryset(request)
        try:
            grouper = int(request.GET.get(GROUPER_PARAM))
        except (TypeError, ValueError):
            raise IncorrectLookupParameters("Missing grouper")
        versioning_extension = apps.get_app_config('djangocms_versioning').cms_extension
        versionable = versioning_extension.versionables_by_content[self.model_admin.model._source_model]
        content_objects = versionable.for_grouper(grouper)
        return qs.filter(object_id__in=content_objects)


class VersionAdmin(admin.ModelAdmin):
    """Admin class used for version models.
    """

    # disable delete action
    actions = None

    list_display = (
        'pk',
        'created',
        'content_link',
        'state',
        'state_actions',
    )
    list_display_links = None

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('content')

    def get_changelist(self, request, **kwargs):
        return VersionChangeList

    def content_link(self, obj):
        content = obj.content
        url = reverse('admin:{app}_{model}_change'.format(
            app=content._meta.app_label,
            model=content._meta.model_name,
        ), args=[content.pk])
        return format_html(
            '<a href="{url}">{label}</a>',
            url=url,
            label=content,
        )
    content_link.short_description = _('Content')
    content_link.admin_order_field = 'content'

    def state_actions(self, obj):
        """Display links to state change endpoints
        """
        archive_url = reverse('admin:djangocms_versioning_{model}_archive'.format(
            model=self.model.__name__.lower(),
        ), args=(obj.pk,))
        archive_icon = '<a href="{archive_url}">Archive</a>'.format(
            archive_url=archive_url)
        all_actions = ''
        if obj.state == DRAFT:
            all_actions += archive_icon
        return format_html(all_actions)

    def grouper_form_view(self, request):
        """Displays an intermediary page to select a grouper object
        to show versions of.
        """
        context = dict(
            self.admin_site.each_context(request),
            opts=self.model._meta,
            form=grouper_form_factory(self.model._source_model)(),
        )
        return render(request, 'djangocms_versioning/admin/grouper_form.html', context)

    def _get_grouper(self, version_obj):
        """Helper method to get the grouper from the version object
        """
        versioning_extension = apps.get_app_config(
            'djangocms_versioning').cms_extension
        versionable = versioning_extension.versionables_by_content[
            version_obj.content.__class__]
        return getattr(version_obj.content, versionable.grouper_field_name)

    def archive_view(self, request, pk):
        """Archives the specified version and redirects back to the
        version changelist
        """
        # FIXME: We should be using POST only for this, but some frontend
        # issues need to be solved first. The code below just needs to
        # be uncommented and a test is also already written (but currently
        # being skipped) to handle the POST-only approach

        # This view always changes data so only POST requests should work
        # if request.method != 'POST':
        #     raise Http404

        version = self.model.objects.get(pk=pk)
        # Raise 404 if not in draft status
        if version.state != DRAFT:
            raise Http404
        # Archive the version
        version.archive(request.user)
        version.save()
        # Display message
        messages.success(request, "Version archived")
        # Redirect
        grouper = self._get_grouper(version)
        url = reverse('admin:{app}_{model}_changelist'.format(
            app=self.model._meta.app_label,
            model=self.model._meta.model_name,
        )) + '?grouper=' + str(grouper.pk)
        return redirect(url)

    def changelist_view(self, request, extra_context=None):
        if not request.GET:
            # redirect to grouper form when there's no GET parameters
            opts = self.model._meta
            return redirect(reverse('admin:{}_{}_grouper'.format(
                opts.app_label,
                opts.model_name,
            )))
        return super().changelist_view(request, extra_context)

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        return [
            url(
                r'^grouper/$',
                self.admin_site.admin_view(self.grouper_form_view),
                name='{}_{}_grouper'.format(*info),
            ),
            url(
                r'^(.+)/archive/$',
                self.admin_site.admin_view(self.archive_view),
                name='{}_{}_archive'.format(*info),
            ),
        ] + super().get_urls()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        """Return True for changelist and False for change view.
        """
        return obj is None

    def has_delete_permission(self, request, obj=None):
        return False
