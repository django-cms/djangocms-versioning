from cms.app_base import CMSAppConfig

from djangocms_versioning.datastructures import VersionableItem, default_copy

from .models import BlogContent, CommentContent


class BlogpostCMSConfig(CMSAppConfig):
    djangocms_versioning_enabled = True
    versioning = [
        VersionableItem(
            content_model=BlogContent,
            grouper_field_name="blogpost",
            copy_function=default_copy,
        ),
        VersionableItem(
            content_model=CommentContent,
            grouper_field_name="comment",
            copy_function=default_copy,
        ),
    ]
