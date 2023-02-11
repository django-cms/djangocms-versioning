from django.contrib import admin

from djangocms_versioning.admin import ExtendedVersionAdminMixin
from djangocms_versioning.indicators import indicator_mixin_factory
from djangocms_versioning.test_utils.blogpost import models


class BlogContentAdmin(
    indicator_mixin_factory(),
    ExtendedVersionAdminMixin,
    admin.ModelAdmin
):
    pass


class BlogPostAdmin(
    indicator_mixin_factory(),
    ExtendedVersionAdminMixin,
    admin.ModelAdmin
):
    pass


admin.site.register(models.BlogPost, BlogPostAdmin)
admin.site.register(models.BlogContent, BlogContentAdmin)
