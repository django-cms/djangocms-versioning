from django.apps import apps

from cms.test_utils.testcases import CMSTestCase
from cms.api import create_page, create_title, add_plugin
from cms.models import PageContent
from cms.toolbar.utils import get_object_preview_url
from cms.toolbar.utils import get_object_edit_url

from djangocms_versioning.constants import DRAFT, PUBLISHED


class ViewTests(CMSTestCase):
    """
    Testing that rendering works as expected for pagecontent in different
    languages and in combination with toolbars.
    """

    def setUp(self):
        super().setUp()
        self.user = self.get_superuser()
        self.client.force_login(self.user)
        defaults = {
            'template': 'page.html',
            'created_by': self.user
        }
        self.page = create_page('english page', language='en', **defaults)
        self.english = PageContent._original_manager.get(language='en')
        self.english.versions.all()[0].publish(self.user)

        self.german = create_title(
            'de', 'german content', self.page, created_by=self.user
        )

        pl_en = self.english.get_placeholders()[0]
        pl_de = self.german.get_placeholders()[0]

        add_plugin(pl_en, 'TextPlugin', 'en', body='english body')
        add_plugin(pl_de, 'TextPlugin', 'de', body='german body')

        german_version = self.german.versions.all()[0]
        self.german_url = '/de/german-content/'
        self.assertEqual(german_version.state, DRAFT)

    def test_normal_view(self):
        """User is authenticated and able to visit draft url without 404"""
        response = self.client.get(self.german_url)

        self.assertEqual(response.request['PATH_INFO'], self.german_url)
        self.assertContains(response, 'german body')

        edit_url = response.context['cms_edit_url']
        preview_url = response.context['cms_preview_url']

        expected_edit_url = get_object_edit_url(self.german, 'de')
        expected_preview_url = get_object_preview_url(self.german, 'de')

        self.assertEqual(edit_url, expected_edit_url)
        self.assertEqual(preview_url, expected_preview_url)

    def test_normal_view_logged_out(self):
        """A page in draft should give you a 404 if you visit the public url"""
        self.client.logout()
        response = self.client.get(self.german_url)

        self.assertEqual(response.status_code, 404)

    def test_absolute_url_of_draft(self):
        self.assertEqual(self.german.get_absolute_url(), '/de/german-content/')

    def test_visit_page_edit_url(self):
        """
        Pagecontent in draft for edit url should be displaying its language content
        """
        edit_url = get_object_edit_url(self.german, 'de')
        response = self.client.get(edit_url)

        self.assertContains(response, 'german body')

    def test_toolbar_shows_correct_language_for_draft_german(self):
        """Visiting german draft in german layout"""
        edit_url = get_object_edit_url(self.german, 'de')
        response = self.client.get(edit_url)

        toolbar = response.context['cms_toolbar']
        lang_menu = toolbar.menus['language-menu']
        items = lang_menu.items

        self.assertContains(response, 'german body')

        self.assertEqual(items[0].name, 'English')
        self.assertEqual(items[0].active, False, 'English should not be active')

        self.assertEqual(items[1].name, 'Deutsche')
        self.assertEqual(items[1].active, True, 'German should be active')
        self.assertEqual(toolbar.get_object().pk, self.german.pk)

    def test_toolbar_shows_correct_content_for_german_draft_in_english(self):
        """Visiting german draft with english layout"""
        edit_url = get_object_edit_url(self.german, 'en')
        response = self.client.get(edit_url)

        toolbar = response.context['cms_toolbar']
        lang_menu = toolbar.menus['language-menu']
        items = lang_menu.items

        self.assertContains(response, 'german body')

        self.assertEqual(items[0].name, 'English')
        self.assertEqual(items[0].active, False, 'English should not be active')

        self.assertEqual(items[1].name, 'Deutsche')
        self.assertEqual(items[1].active, True, 'German should be active')
        self.assertEqual(toolbar.get_object().pk, self.german.pk)
