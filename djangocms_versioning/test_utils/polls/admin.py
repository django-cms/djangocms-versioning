from django.conf.urls import url
from django.contrib import admin

from djangocms_versioning.admin import ExtendedVersionAdminMixin

from .models import Answer, Poll, PollContent
from .views import PreviewView


@admin.register(PollContent)
class PollContentAdmin(ExtendedVersionAdminMixin, admin.ModelAdmin):
    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        return [
            url(
                r"^(?P<id>\d+)/preview/$",
                self.admin_site.admin_view(PreviewView.as_view()),
                name="{}_{}_preview".format(*info),
            )
        ] + super().get_urls()

    def get_version_link(self):
        return


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    pass


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    pass
