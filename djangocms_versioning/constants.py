from django.utils.translation import gettext_lazy as _


"""Version states"""
ARCHIVED = "archived"
DRAFT = "draft"
PUBLISHED = "published"
UNPUBLISHED = "unpublished"

VERSION_STATES = (
    (DRAFT, _("Draft")),
    (PUBLISHED, _("Published")),
    (UNPUBLISHED, _("Unpublished")),
    (ARCHIVED, _("Archived")),
)
"""Version operation states"""
OPERATION_ARCHIVE = "operation_archive"
OPERATION_DRAFT = "operation_draft"
OPERATION_PUBLISH = "operation_publish"
OPERATION_UNPUBLISH = "operation_unpublish"
