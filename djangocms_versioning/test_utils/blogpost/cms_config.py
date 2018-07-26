from cms.app_base import CMSAppConfig

from djangocms_versioning import Versionable

from .models import BlogPost, BlogContent, Comment


class BlogpostCMSConfig(CMSAppConfig):
    djangocms_versioning_enabled = True
    versioning = [
        Versionable(
            grouper=BlogPost,
            content=BlogContent,
        ),
    ]
