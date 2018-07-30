from cms.app_base import CMSAppConfig

from djangocms_versioning.versionable import Versionable

from .models import BlogContent, BlogPost, Comment, CommentContent


class BlogpostCMSConfig(CMSAppConfig):
    djangocms_versioning_enabled = True
    versioning = [
        Versionable(
            grouper=BlogPost,
            content=BlogContent,
        ),
        Versionable(
            grouper=Comment,
            content=CommentContent,
        ),
    ]
