from cms.app_base import CMSAppConfig

from djangocms_versioning.versionable import Versionable

from .models import Poll, PollContent


class PollsCMSConfig(CMSAppConfig):
    djangocms_versioning_enabled = True
    versioning = [
        Versionable(
            grouper=Poll,
            content=PollContent,
        ),
    ]
