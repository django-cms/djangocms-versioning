from cms.app_base import CMSAppConfig

from djangocms_versioning.datastructures import VersionableItem

from .models import BlogContent, CommentContent


class BlogpostCMSConfig(CMSAppConfig):
    djangocms_versioning_enabled = True
    versioning = [
        VersionableItem(
            content_model=BlogContent,
            grouper_field_name='blogpost',
        ),
        VersionableItem(
            content_model=CommentContent,
            grouper_field_name='comment',
        ),
    ]
