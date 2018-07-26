from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from .models import Version


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
        latest_versions = Version.objects.distinct_groupers(queryset.model)
        return queryset.filter(pk__in=latest_versions.values('object_id'))


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
