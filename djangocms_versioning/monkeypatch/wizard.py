from django.apps import apps

from cms.cms_wizards import CMSPageWizard, CMSSubPageWizard
from cms.toolbar.utils import get_object_preview_url
from cms.wizards.wizard_base import Wizard

from djangocms_versioning.constants import DRAFT


def get_wizard_success_url(self, obj, **kwargs):
    language = kwargs.get('language', None)
    return get_object_preview_url(obj, language)
Wizard.get_success_url = get_wizard_success_url


def get_page_wizard_success_url(self, obj, **kwargs):
    language = kwargs['language']
    cms_extension = apps.get_app_config('djangocms_versioning').cms_extension
    versionable_item = cms_extension.versionables_by_grouper[obj.__class__]
    page_content = (
        versionable_item
        .for_grouper(obj)
        .filter(
            language=language,
            versions__state=DRAFT,
        )
        .first()
    )
    return get_wizard_success_url(self, page_content, **kwargs)
CMSPageWizard.get_success_url = get_page_wizard_success_url
CMSSubPageWizard.get_success_url = get_page_wizard_success_url
