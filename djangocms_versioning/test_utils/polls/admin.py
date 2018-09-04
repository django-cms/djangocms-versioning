from django.contrib import admin

from .models import Answer, Poll, PollContent


@admin.register(PollContent)
class PollContentAdmin(admin.ModelAdmin):
    pass


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    pass


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    pass
