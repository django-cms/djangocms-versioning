from cms.app_base import CMSAppConfig

from .models import FancyPoll
from .views import render_content


class FancyPollCMSConfig(CMSAppConfig):
    cms_enabled = True
    cms_toolbar_enabled_models = [(FancyPoll, render_content)]
    djangocms_versioning_enabled = False
    versioning = []
