from django.contrib import admin

from djangocms_versioning.admin import ExtendedVersionAdminMixin
from djangocms_versioning.test_utils.blogpost import models


class BlogContentAdmin(ExtendedVersionAdminMixin, admin.ModelAdmin):
    pass


admin.site.register(models.BlogPost)
admin.site.register(models.BlogContent, BlogContentAdmin)
