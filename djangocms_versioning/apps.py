from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class VersioningConfig(AppConfig):
    name = 'djangocms_versioning'
    verbose_name = _('django CMS Versioning')

    def ready(self):
        from . import monkeypatch
