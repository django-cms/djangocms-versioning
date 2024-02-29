from django.conf import settings

ENABLE_MENU_REGISTRATION = getattr(
    settings, "DJANGOCMS_VERSIONING_ENABLE_MENU_REGISTRATION", True
)

USERNAME_FIELD = getattr(
    settings, "DJANGOCMS_VERSIONING_USERNAME_FIELD", "username"
)

DEFAULT_USER = getattr(
    settings, "DJANGOCMS_VERSIONING_DEFAULT_USER", None
)

ALLOW_DELETING_VERSIONS = getattr(
    settings, "DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS", False
)

LOCK_VERSIONS = getattr(
    settings, "DJANGOCMS_VERSIONING_LOCK_VERSIONS", False,
)

VERBOSE = getattr(
    settings, "DJANGOCMS_VERSIONING_VERBOSE", True,
)

EMAIL_NOTIFICATIONS_FAIL_SILENTLY = getattr(
    settings, "EMAIL_NOTIFICATIONS_FAIL_SILENTLY", False
)

ON_PUBLISH_REDIRECT = getattr(
    settings, "DJANGOCMS_VERISONING_ON_PUBLISH_REDIRECT", "published"
)
#: Allowed values: "versions", "published", "preview"
