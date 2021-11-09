from django.contrib import admin

from cms.extensions import TitleExtensionAdmin

from .models import PollExtension


@admin.register(PollExtension)
class PollExtensionAdmin(TitleExtensionAdmin):
    pass
