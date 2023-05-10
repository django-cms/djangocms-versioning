from cms.extensions import PageContentExtensionAdmin
from django.contrib import admin

from .models import PollPageContentExtension


@admin.register(PollPageContentExtension)
class PollExtensionAdmin(PageContentExtensionAdmin):

    pass
