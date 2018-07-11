from cms.app_base import CMSAppConfig

from .models import BlogPostVersion, CommentVersion


class BlogpostCMSConfig(CMSAppConfig):
    djangocms_versioning_enabled = True
    versioning_models = [BlogPostVersion, CommentVersion]
    versioning_content_types = [
        {'grouper': 'post',
         'content': '.....',
         'version': '# insert_version_object'},
        {'grouper': 'post',
         'content': '.....',
         'version': '# insert_version_object'},
    ]

