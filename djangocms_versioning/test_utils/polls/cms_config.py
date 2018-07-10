from cms.app_base import CMSAppConfig

from .models import PollVersion

class PollsCMSConfig(CMSAppConfig):
    djangocms_versioning_enabled = True

    versioning_models = [PollVersion]

    versioning_content_types = [
        {'grouper': 'post',
         'content': '.....',
         'version': '# insert_version_object'},
        {'grouper': 'post',
         'content': '.....',
         'version': '# insert_version_object'},
    ]

