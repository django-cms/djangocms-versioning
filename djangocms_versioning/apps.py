from django.apps import AppConfig
from django.db.models.signals import post_save
from django.utils.translation import gettext_lazy as _


class VersioningConfig(AppConfig):
    name = "djangocms_versioning"
    verbose_name = _("django CMS Versioning")
    default_auto_field = "django.db.models.AutoField"

    def ready(self):
        from cms.models import contentmodels, fields
        from cms.signals import post_obj_operation, post_placeholder_operation

        from .conf import LOCK_VERSIONS
        from .handlers import (
            update_modified_date,
            update_modified_date_for_pagecontent,
            update_modified_date_for_placeholder_source,
        )
        from .helpers import is_content_editable, placeholder_content_is_unlocked_for_user

        # Add check to PlaceholderRelationField
        fields.PlaceholderRelationField.default_checks += [is_content_editable]
        if LOCK_VERSIONS:
            fields.PlaceholderRelationField.default_checks += [placeholder_content_is_unlocked_for_user]

        # Remove uniqueness constraint from PageContent model to allow for different versions
        pagecontent_unique_together = tuple(
            set(contentmodels.PageContent._meta.unique_together) - {("language", "page")}
        )
        contentmodels.PageContent._meta.unique_together = pagecontent_unique_together

        # Connect signals
        post_save.connect(update_modified_date, dispatch_uid="versioning")
        post_placeholder_operation.connect(
            update_modified_date_for_placeholder_source, dispatch_uid="versioning"
        )
        post_obj_operation.connect(
            update_modified_date_for_pagecontent, dispatch_uid="versioning"
        )
