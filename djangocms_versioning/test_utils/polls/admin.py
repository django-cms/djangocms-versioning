from django.contrib import admin

from .models import PollContent


@admin.register(PollContent)
class PollContentAdmin(admin.ModelAdmin):
    pass
