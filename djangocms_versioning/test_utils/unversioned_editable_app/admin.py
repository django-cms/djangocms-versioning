from cms.admin.placeholderadmin import FrontendEditableAdminMixin
from django.contrib import admin

from .models import FancyPoll


class FancyPollAdmin(FrontendEditableAdminMixin, admin.ModelAdmin):
    pass


admin.site.register(FancyPoll, FancyPollAdmin)
