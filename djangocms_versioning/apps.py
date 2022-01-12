from django.apps import AppConfig
from django.db.models.signals import post_save
from django.utils.translation import gettext_lazy as _


class VersioningConfig(AppConfig):
    name = "djangocms_versioning"
    verbose_name = _("django CMS Versioning")

    def ready(self):
        from cms.signals import post_obj_operation, post_placeholder_operation

        from . import monkeypatch  # noqa: F401
        from .handlers import (
            update_modified_date,
            update_modified_date_for_pagecontent,
            update_modified_date_for_placeholder_source,
        )

        post_save.connect(update_modified_date, dispatch_uid="versioning")
        post_placeholder_operation.connect(
            update_modified_date_for_placeholder_source, dispatch_uid="versioning"
        )
        post_obj_operation.connect(
            update_modified_date_for_pagecontent, dispatch_uid="versioning"
        )
