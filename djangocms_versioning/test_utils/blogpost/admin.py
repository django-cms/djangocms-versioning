from django.contrib import admin

from cms.admin.utils import GrouperModelAdmin

from djangocms_versioning.admin import (
    ExtendedGrouperVersionAdminMixin,
    ExtendedVersionAdminMixin,
    StateIndicatorMixin,
)
from djangocms_versioning.test_utils.blogpost import models


class BlogContentAdmin(StateIndicatorMixin, ExtendedVersionAdminMixin, admin.ModelAdmin):
    list_display = ("__str__", "state_indicator")


class BlogPostAdmin(StateIndicatorMixin, ExtendedGrouperVersionAdminMixin, GrouperModelAdmin):
    content_model = models.BlogContent  # Non-standard naming
    list_display = ("__str__", "state_indicator")


admin.site.register(models.BlogPost, BlogPostAdmin)
admin.site.register(models.BlogContent, BlogContentAdmin)
