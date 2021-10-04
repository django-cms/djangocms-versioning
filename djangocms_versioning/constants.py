"""Version states"""
ARCHIVED = "archived"
DRAFT = "draft"
PUBLISHED = "published"
UNPUBLISHED = "unpublished"
VERSION_STATES = (
    (DRAFT, "Draft"),
    (PUBLISHED, "Published"),
    (UNPUBLISHED, "Unpublished"),
    (ARCHIVED, "Archived"),
)
"""Version operation states"""
OPERATION_ARCHIVE = "operation_archive"
OPERATION_DRAFT = "operation_draft"
OPERATION_PUBLISH = "operation_publish"
OPERATION_UNPUBLISH = "operation_unpublish"
