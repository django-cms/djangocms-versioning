from cms.app_base import CMSAppConfig

from djangocms_versioning.models import PollVersion


class PollsCMSConfig(CMSAppConfig):
    djangocms_versioning_enabled = True
    versioning_models = [PollVersion]
