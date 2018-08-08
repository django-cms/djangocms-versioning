from cms.app_base import CMSAppConfig

from djangocms_versioning.datastructures import VersionableItem

from .models import PollContent


class PollsCMSConfig(CMSAppConfig):
    djangocms_versioning_enabled = True
    versioning = [
        VersionableItem(
            content_model=PollContent,
            grouper_field_name='poll',
            copy_functions={
                'answer.poll_content': lambda old_value: old_value
            }
        ),
    ]
