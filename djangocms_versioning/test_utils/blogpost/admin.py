from django.contrib import admin

from djangocms_versioning.admin import ExtendedVersionAdminMixin
from djangocms_versioning.indicators import IndicatorMixin
from djangocms_versioning.test_utils.blogpost import models


class BlogContentAdmin(IndicatorMixin, ExtendedVersionAdminMixin, admin.ModelAdmin):
    pass


class BlogPostAdmin(IndicatorMixin, ExtendedVersionAdminMixin, admin.ModelAdmin):
    pass


admin.site.register(models.BlogPost, BlogPostAdmin)
admin.site.register(models.BlogContent, BlogContentAdmin)
