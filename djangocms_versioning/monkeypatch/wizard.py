from django.apps import apps

from cms.cms_wizards import CMSPageWizard, CMSSubPageWizard
from cms.toolbar.utils import get_object_preview_url
from cms.utils.helpers import is_editable_model
from cms.utils.patching import patch_cms
from cms.wizards.wizard_base import Wizard

from djangocms_versioning.constants import DRAFT


original_get_wizard_success_url = Wizard.get_success_url


def get_wizard_success_url(self, obj, **kwargs):  # noqa: E302
    cms_extension = apps.get_app_config("djangocms_versioning").cms_extension
    model = obj.__class__
    if cms_extension.is_content_model_versioned(model) and is_editable_model(model):
        language = kwargs.get("language", None)
        return get_object_preview_url(obj, language)
    return original_get_wizard_success_url(self, obj, **kwargs)


patch_cms(Wizard, "get_success_url", get_wizard_success_url)


def get_page_wizard_success_url(self, obj, **kwargs):
    language = kwargs["language"]
    cms_extension = apps.get_app_config("djangocms_versioning").cms_extension
    versionable_item = cms_extension.versionables_by_grouper[obj.__class__]
    page_content = (
        versionable_item.for_grouper(obj)
        .filter(language=language, versions__state=DRAFT)
        .first()
    )
    return get_wizard_success_url(self, page_content, **kwargs)


patch_cms(CMSPageWizard, "get_success_url", get_page_wizard_success_url)
patch_cms(CMSSubPageWizard, "get_success_url", get_page_wizard_success_url)
