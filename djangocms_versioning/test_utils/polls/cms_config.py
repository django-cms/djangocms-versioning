from cms.app_base import CMSAppConfig

<<<<<<< HEAD
from .models import PollVersion

class PollsCMSConfig(CMSAppConfig):
    djangocms_versioning_enabled = True

    versioning_models = [PollVersion]
=======
class PollsCMSConfig(CMSAppConfig):
    djangocms_versioning_enabled = True

    versioning_models = ['PollsVersion']
>>>>>>> 6e3b4fd22f701ced488c3740a2875acf44ae4932
    versioning_content_types = [
        {'grouper': 'post',
         'content': '.....',
         'version': '# insert_version_object'},
        {'grouper': 'post',
         'content': '.....',
         'version': '# insert_version_object'},
    ]

