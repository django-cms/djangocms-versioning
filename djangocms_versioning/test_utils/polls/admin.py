from cms.admin.utils import GrouperModelAdmin
from django.contrib import admin
from django.urls import re_path

from djangocms_versioning.admin import (
    ExtendedVersionAdminMixin,
)

from .models import Answer, Poll, PollContent
from .views import PreviewView


@admin.register(PollContent)
class PollContentAdmin(ExtendedVersionAdminMixin, admin.ModelAdmin):
    list_display = ("text", )

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        return [
            re_path(
                r"^(?P<id>\d+)/preview/$",
                self.admin_site.admin_view(PreviewView.as_view()),
                name="{}_{}_preview".format(*info),
            )
        ] + super().get_urls()


@admin.register(Poll)
class PollAdmin(GrouperModelAdmin):
    list_display = ("content__text", "get_author", "get_modified_date", "get_versioning_state", "admin_list_actions")


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    pass
