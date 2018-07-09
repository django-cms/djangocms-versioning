from cms.app_base import CMSAppConfig


class BlogpostCMSConfig(CMSAppConfig):
    djangocms_versioning_enabled = True

    versioning_models = ['BlogpostVersion']
    versioning_content_types = [
        {'grouper': 'post',
         'content': '.....',
         'version': '# insert_version_object'},
        {'grouper': 'post',
         'content': '.....',
         'version': '# insert_version_object'},
    ]

