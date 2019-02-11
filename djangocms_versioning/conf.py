from django.conf import settings


ENABLE_MENU_REGISTRATION = getattr(
    settings,
    'DJANGOCMS_VERSIONING_ENABLE_MENU_REGISTRATION',
    True,
)
