from django.contrib import admin

from cms.extensions import PageContentExtensionAdmin

from .models import PollPageContentExtension


@admin.register(PollPageContentExtension)
class PollExtensionAdmin(PageContentExtensionAdmin):

    pass
