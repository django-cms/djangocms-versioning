from cms.app_base import CMSAppConfig

class PollsCMSConfig(CMSAppConfig):
    djangocms_versioning_enabled = True

    versioning_models = ['PollsVersion']
    versioning_content_types = [
        {'grouper': 'post',
         'content': '.....',
         'version': '# insert_version_object'},
        {'grouper': 'post',
         'content': '.....',
         'version': '# insert_version_object'},
    ]

