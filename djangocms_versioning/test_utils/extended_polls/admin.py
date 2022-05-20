from django.contrib import admin

from cms.extensions import TitleExtensionAdmin

from .models import PollTitleExtension


@admin.register(PollTitleExtension)
class PollExtensionAdmin(TitleExtensionAdmin):
    pass
