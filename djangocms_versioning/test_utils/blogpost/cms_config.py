from cms.app_base import CMSAppConfig

from .models import BlogPostVersion, CommentVersion


class BlogpostCMSConfig(CMSAppConfig):
    djangocms_versioning_enabled = True
    versioning_models = [BlogPostVersion, CommentVersion]
