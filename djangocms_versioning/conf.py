from django.conf import settings


ENABLE_MENU_REGISTRATION = getattr(
    settings, "DJANGOCMS_VERSIONING_ENABLE_MENU_REGISTRATION", True
)

USERNAME_FIELD = getattr(
    settings, "DJANGOCMS_VERSIONING_USERNAME_FIELD", 'username'
)
