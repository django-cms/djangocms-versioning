from django.apps import apps
from django.contrib import admin
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.views.main import ChangeList
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

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
            Version.objects.create(content=obj)

    def get_queryset(self, request):
        """Limit query to most recent content versions
        """
        queryset = super().get_queryset(request)
        versioning_extension = apps.get_app_config('djangocms_versioning').cms_extension
        versionable = versioning_extension.versionables.by_content[queryset.model]
        return queryset.filter(pk__in=versionable.distinct_groupers())


class VersionChangeList(ChangeList):

    def get_filters_params(self, params=None):
        params = super().get_filters_params(params)
        params.pop(GROUPER_PARAM, None)
        return params

    def get_queryset(self, request):
        try:
            grouper = int(request.GET.get(GROUPER_PARAM))
        except (TypeError, ValueError):
            raise IncorrectLookupParameters("Invalid grouper")
        content_type_id = request.GET.get('content_type_id')
        try:
            content_type = ContentType.objects.get(pk=content_type_id)
            model = content_type.model_class()
        except (ContentType.DoesNotExist, ValueError):
            raise IncorrectLookupParameters("Invalid content_type_id")
        qs = super().get_queryset(request)
        if grouper is None:
            return qs
        versioning_extension = apps.get_app_config('djangocms_versioning').cms_extension
        versionable = versioning_extension.versionables.by_content[model]
        object_ids = model.objects.filter(**{versionable.grouper_field.name: grouper})
        return qs.filter(
            object_id__in=object_ids,
        )


@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    """Admin class used for version models.
    """

    # disable delete action
    actions = None

    list_display = (
        'pk',
        'content_link',
        'label',
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

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        """Return True for changelist and False for change view.
        """
        return obj is None

    def has_delete_permission(self, request, obj=None):
        return False
