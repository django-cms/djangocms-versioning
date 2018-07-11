from cms.app_base import CMSAppConfig

from djangocms_versioning.test_utils.polls.models import PollVersion


class PollsCMSConfig(CMSAppConfig):
    djangocms_versioning_enabled = True
    versioning_models = [PollVersion]
