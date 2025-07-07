from cms import __version__ as CMS_VERSION
from django.conf import settings

ENABLE_MENU_REGISTRATION = getattr(
    settings, "DJANGOCMS_VERSIONING_ENABLE_MENU_REGISTRATION", CMS_VERSION <= "4.1.0"
)
if CMS_VERSION.startswith("5."):
    ENABLE_MENU_REGISTRATION = False

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

VERBOSE_UI = getattr(
    settings, "DJANGOCMS_VERSIONING_VERBOSE_UI", True
)
#: If True, the version admin will be offered in the admin index
#: for each registered versionable model.
