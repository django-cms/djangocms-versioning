from django.apps import apps
from django.conf.urls import url
from django.contrib import admin, messages
from django.contrib.admin.options import (
    TO_FIELD_VAR,
    IncorrectLookupParameters,
)
from django.contrib.admin.utils import unquote
from django.contrib.admin.views.main import ChangeList
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from cms.toolbar.utils import get_object_edit_url, get_object_preview_url
from cms.utils import get_language_from_request
from cms.utils.helpers import is_editable_model

from .constants import DRAFT, PUBLISHED
from .forms import grouper_form_factory
from .models import Version


GROUPER_PARAM = 'grouper'


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
            # create a new version object and save it
            Version.objects.create(content=obj, created_by=request.user)

    def get_queryset(self, request):
        """Limit query to most recent content versions
        """
        from .helpers import override_default_manager
        with override_default_manager(self.model, self.model._original_manager):
            queryset = super().get_queryset(request)
        versioning_extension = apps.get_app_config('djangocms_versioning').cms_extension
        versionable = versioning_extension.versionables_by_content[queryset.model]
        return queryset.filter(pk__in=versionable.distinct_groupers())

    def change_view(self, request, object_id, form_url='', extra_context=None):
        # Raise 404 if the version associated with the object is not
        # a draft
        to_field = request.POST.get(TO_FIELD_VAR, request.GET.get(TO_FIELD_VAR))
        content_obj = self.get_object(request, unquote(object_id), to_field)
        if content_obj is not None:
            version = Version.objects.get_for_content(content_obj)
            if version.state != DRAFT:
                raise Http404
        return super().change_view(
            request, object_id, form_url='', extra_context=None)


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
        content_model = self.model_admin.model._source_model
        versioning_extension = apps.get_app_config('djangocms_versioning').cms_extension
        versionable = versioning_extension.versionables_by_content[content_model]
        try:
            grouper = versionable.grouper_model.objects.get(
                pk=int(request.GET.get(GROUPER_PARAM)),
            )
        except (ObjectDoesNotExist, TypeError, ValueError):
            raise IncorrectLookupParameters("Missing grouper")
        return qs.filter_by_grouper(grouper)


class VersionAdmin(admin.ModelAdmin):
    """Admin class used for version models.
    """

    class Media:
        js = ('djangocms_versioning/js/actions.js',)
        css = {
            'all': ('djangocms_versioning/css/actions.css',)
        }

    # register custom actions
    actions = ['compare_versions']

    list_display = (
        'nr',
        'created',
        'content_link',
        'created_by',
        'state',
        'state_actions',
    )
    list_display_links = None

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('content')

    def get_changelist(self, request, **kwargs):
        return VersionChangeList

    def get_actions(self, request):
        actions = super().get_actions(request)
        # disable delete action
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def nr(self, obj):
        """Get the identifier of the version. Might be something other
        than the pk eventually.
        """
        return obj.pk
    nr.admin_order_field = 'pk'

    def content_link(self, obj):
        content = obj.content

        # If the object is editable the preview view should be used.
        if is_editable_model(content.__class__):
            url = get_object_preview_url(content)
        # Or else, the standard change view should be used
        else:
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

    def _get_archive_link(self, obj):
        """Helper function to get the html link to the archive action
        """
        if not obj.state == DRAFT:
            # Don't display the link if it can't be archived
            return ''
        archive_url = reverse('admin:{app}_{model}_archive'.format(
            app=obj._meta.app_label, model=self.model._meta.model_name,
        ), args=(obj.pk,))
        return render_to_string(
            'djangocms_versioning/admin/archive_icon.html',
            {'archive_url': archive_url}
        )

    def _get_publish_link(self, obj):
        """Helper function to get the html link to the publish action
        """
        if not obj.state == DRAFT:
            # Don't display the link if it can't be published
            return ''
        publish_url = reverse('admin:{app}_{model}_publish'.format(
            app=obj._meta.app_label, model=self.model._meta.model_name,
        ), args=(obj.pk,))
        return render_to_string(
            'djangocms_versioning/admin/publish_icon.html',
            {'publish_url': publish_url}
        )

    def _get_unpublish_link(self, obj):
        """Helper function to get the html link to the unpublish action
        """
        if not obj.state == PUBLISHED:
            # Don't display the link if it can't be unpublished
            return ''
        unpublish_url = reverse('admin:{app}_{model}_unpublish'.format(
            app=obj._meta.app_label, model=self.model._meta.model_name,
        ), args=(obj.pk,))
        return render_to_string(
            'djangocms_versioning/admin/unpublish_icon.html',
            {'unpublish_url': unpublish_url}
        )

    def _get_edit_link(self, obj):
        """Helper function to get the html link to the edit action
        """
        if obj.state == PUBLISHED:
            pks_for_grouper = obj.versionable.for_grouper(
                obj.grouper).values_list('pk', flat=True)
            drafts = Version.objects.filter(
                object_id__in=pks_for_grouper, content_type=obj.content_type,
                state=DRAFT)
            if drafts.exists():
                return ''
        elif not obj.state == DRAFT:
            # Don't display the link if it's a draft
            return ''
        edit_url = reverse('admin:{app}_{model}_edit_redirect'.format(
            app=obj._meta.app_label, model=self.model._meta.model_name,
        ), args=(obj.pk,))
        return render_to_string(
            'djangocms_versioning/admin/edit_icon.html',
            {'edit_url': edit_url}
        )

    def state_actions(self, obj):
        """Display links to state change endpoints
        """
        archive_link = self._get_archive_link(obj)
        publish_link = self._get_publish_link(obj)
        unpublish_link = self._get_unpublish_link(obj)
        edit_link = self._get_edit_link(obj)
        return format_html(
            edit_link + publish_link + unpublish_link + archive_link)
    state_actions.short_description = 'actions'

    def compare_versions(self, request, queryset):
        """
        Redirects to a compare versions view based on a users choice
        """
        # Validate that only two versions are selected
        if queryset.count() != 2:
            self.message_user(request, _("Exactly two versions need to be selected."))
            return

        # Build the link for the version comparison of the two selected versions
        url = reverse('admin:{app}_{model}_compare'.format(
            app=self.model._meta.app_label,
            model=self.model._meta.model_name,
        ), args=(queryset[0].pk,))
        url += '?compare_to=%d' % queryset[1].pk

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
        return render(request, 'djangocms_versioning/admin/grouper_form.html', context)

    def archive_view(self, request, object_id):
        """Archives the specified version and redirects back to the
        version changelist
        """
        # This view always changes data so only POST requests should work
        if request.method != 'POST':
            return HttpResponseNotAllowed(['POST'], 'This view only supports POST method.')

        # Check version exists
        version = self.get_object(request, unquote(object_id))
        if version is None:
            return self._get_obj_does_not_exist_redirect(
                request, self.model._meta, object_id)
        # Raise 404 if not in draft status
        if version.state != DRAFT:
            raise Http404
        # Archive the version
        version.archive(request.user)
        # Display message
        messages.success(request, _("Version archived"))
        # Redirect
        url = reverse('admin:{app}_{model}_changelist'.format(
            app=self.model._meta.app_label,
            model=self.model._meta.model_name,
        )) + '?grouper=' + str(version.grouper.pk)
        return redirect(url)

    def publish_view(self, request, object_id):
        """Publishes the specified version and redirects back to the
        version changelist
        """
        # This view always changes data so only POST requests should work
        if request.method != 'POST':
            return HttpResponseNotAllowed(['POST'], 'This view only supports POST method.')

        # Check version exists
        version = self.get_object(request, unquote(object_id))
        if version is None:
            return self._get_obj_does_not_exist_redirect(
                request, self.model._meta, object_id)
        # Raise 404 if not in draft status
        if version.state != DRAFT:
            raise Http404
        # Publish the version
        version.publish(request.user)
        # Display message
        messages.success(request, _("Version published"))
        # Redirect
        url = reverse('admin:{app}_{model}_changelist'.format(
            app=self.model._meta.app_label,
            model=self.model._meta.model_name,
        )) + '?grouper=' + str(version.grouper.pk)
        return redirect(url)

    def unpublish_view(self, request, object_id):
        """Unpublishes the specified version and redirects back to the
        version changelist
        """
        # This view always changes data so only POST requests should work
        if request.method != 'POST':
            return HttpResponseNotAllowed(['POST'], 'This view only supports POST method.')

        # Check version exists
        version = self.get_object(request, unquote(object_id))
        if version is None:
            return self._get_obj_does_not_exist_redirect(
                request, self.model._meta, object_id)
        # Raise 404 if not in published status
        if version.state != PUBLISHED:
            raise Http404
        # Unpublish the version
        version.unpublish(request.user)
        # Display message
        messages.success(request, _("Version unpublished"))
        # Redirect
        url = reverse('admin:{app}_{model}_changelist'.format(
            app=self.model._meta.app_label,
            model=self.model._meta.model_name,
        )) + '?grouper=' + str(version.grouper.pk)
        return redirect(url)

    def edit_redirect_view(self, request, object_id):
        """Redirects to the admin change view and creates a draft version
        if no draft exists yet.
        """
        # This view always changes data so only POST requests should work
        if request.method != 'POST':
            return HttpResponseNotAllowed(['POST'], 'This view only supports POST method.')

        version = self.get_object(request, unquote(object_id))
        if version is None:
            return self._get_obj_does_not_exist_redirect(
                request, self.model._meta, object_id)
        # If published then there's extra things to do...
        if version.state == PUBLISHED:
            # First check there is no draft record for this grouper
            # already.
            pks_for_grouper = version.versionable.for_grouper(
                version.grouper).values_list('pk', flat=True)
            content_type = ContentType.objects.get_for_model(version.content)
            drafts = Version.objects.filter(
                object_id__in=pks_for_grouper, content_type=content_type,
                state=DRAFT)
            if drafts.exists():
                # There is a draft record so people should be editing
                # the draft record not the published one. Return 404.
                raise Http404
            # If there is no draft record then create a new version
            # that's a draft with the content copied over
            version = version.copy(request.user)
        # Raise 404 if the version is neither draft or published
        elif version.state != DRAFT:
            raise Http404
        # Redirect
        # If the object is editable the cms editable view should be used, with the toolbar.
        if is_editable_model(version.content.__class__):
            url = get_object_edit_url(version.content)
        # Or else, the standard edit view should be used
        else:
            url = reverse('admin:{app}_{model}_change'.format(
                app=version.content._meta.app_label,
                model=version.content._meta.model_name,
            ), args=(version.content.pk,))
        return redirect(url)

    def compare_view(self, request, object_id):
        """Compares two versions
        """
        # Get version 1 (the version we're comparing against)
        v1 = self.get_object(request, unquote(object_id))
        if v1 is None:
            return self._get_obj_does_not_exist_redirect(
                request, self.model._meta, object_id)
        v1_preview_url = reverse(
            'admin:cms_placeholder_render_object_preview',
            args=(v1.content_type_id, v1.object_id))
        # Get the list of versions for the grouper. This is for use
        # in the dropdown to choose a version.
        version_list = Version.objects.filter_by_grouper(v1.grouper)
        # Add the above to context
        context = {
            'version_list': version_list,
            'v1': v1,
            'v1_preview_url': v1_preview_url,
        }
        # Now check if version 2 has been specified and add to context
        # if yes
        if 'compare_to' in request.GET:
            v2 = self.get_object(request, unquote(request.GET['compare_to']))
            if v2 is None:
                return self._get_obj_does_not_exist_redirect(
                    request, self.model._meta, request.GET['compare_to'])
            else:
                context['v2'] = v2
                context['v2_preview_url'] = reverse(
                    'admin:cms_placeholder_render_object_preview',
                    args=(v2.content_type_id, v2.object_id))
        return TemplateResponse(
            request, 'djangocms_versioning/admin/compare.html', context)

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
            url(
                r'^(.+)/publish/$',
                self.admin_site.admin_view(self.publish_view),
                name='{}_{}_publish'.format(*info),
            ),
            url(
                r'^(.+)/unpublish/$',
                self.admin_site.admin_view(self.unpublish_view),
                name='{}_{}_unpublish'.format(*info),
            ),
            url(
                r'^(.+)/edit-redirect/$',
                self.admin_site.admin_view(self.edit_redirect_view),
                name='{}_{}_edit_redirect'.format(*info),
            ),
            url(
                r'^(.+)/compare/$',
                self.admin_site.admin_view(self.compare_view),
                name='{}_{}_compare'.format(*info),
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
