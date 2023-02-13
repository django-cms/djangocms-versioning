from django.contrib import admin

from djangocms_versioning.admin import ExtendedVersionAdminMixin, StateIndicatorMixin
from djangocms_versioning.test_utils.blogpost import models


class BlogContentAdmin(StateIndicatorMixin, ExtendedVersionAdminMixin, admin.ModelAdmin):
    list_display = ("__str__", "indicator")


class BlogPostAdmin(StateIndicatorMixin, ExtendedVersionAdminMixin, admin.ModelAdmin):
    list_display = ("__str__", "state_indicator")


admin.site.register(models.BlogPost, BlogPostAdmin)
admin.site.register(models.BlogContent, BlogContentAdmin)
