from django.contrib import admin

from djangocms_versioning.admin import ExtendedVersionAdminMixin

from .models import IncorrectBlogContent


@admin.register(IncorrectBlogContent)
class IncorrectBlogContentAdmin(ExtendedVersionAdminMixin, admin.ModelAdmin):
    pass


