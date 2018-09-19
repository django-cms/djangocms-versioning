from cms.cms_wizards import cms_page_wizard, cms_subpage_wizard
from cms.test_utils.testcases import CMSTestCase
from cms.toolbar.toolbar import CMSToolbar
from cms.toolbar.utils import get_object_preview_url
from cms.wizards.wizard_base import Wizard

from djangocms_versioning.plugin_rendering import VersionRenderer
from djangocms_versioning.test_utils.factories import (
    PageVersionFactory,
    PollVersionFactory,
)


class MonkeypatchTestCase(CMSTestCase):

    def test_content_renderer(self):
        """Test that cms.toolbar.toolbar.CMSToolbar.content_renderer
        is replaced with a property returning VersionRenderer
        """
        request = self.get_request('/')
        self.assertEqual(
            CMSToolbar(request).content_renderer.__class__,
            VersionRenderer,
        )

    def test_success_url_for_cms_wizard(self):
        from django import forms
        from djangocms_versioning.test_utils.polls.models import PollContent

        # Test against page creations in different languages.
        version = PageVersionFactory(content__language='en')
        self.assertEqual(
            cms_page_wizard.get_success_url(version.content.page, language='en'),
            get_object_preview_url(version.content)
        )

        version = PageVersionFactory(content__language='en')
        self.assertEqual(
            cms_subpage_wizard.get_success_url(version.content.page, language='en'),
            get_object_preview_url(version.content)
        )

        version = PageVersionFactory(content__language='de')
        self.assertEqual(
            cms_page_wizard.get_success_url(version.content.page, language='de'),
            get_object_preview_url(version.content, language='de')
        )

        # Test against non-CMS model.
        class PollForm(forms.ModelForm):
            model = PollContent

        class PollWizard(Wizard):
            pass

        poll_wizard = PollWizard(
            title='Poll Wizard',
            weight=120,
            form=PollForm,
        )
        version = PollVersionFactory()
        self.assertEqual(
            poll_wizard.get_success_url(version.content),
            get_object_preview_url(version.content)
        )
