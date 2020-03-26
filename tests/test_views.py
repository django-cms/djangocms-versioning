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
        """User is authenticated and since only a draft exist they should be seeing a 404"""
        response = self.client.get(self.german_url)

        self.assertEqual(response.status_code, 404)

    def test_normal_view_logged_out(self):
        """A page in draft should give you a 404 if you visit the public url"""
        self.client.logout()
        response = self.client.get(self.german_url)

        self.assertEqual(response.status_code, 404)

    def test_visit_page_edit_url(self):
        """
        Pagecontent in draft for edit url should be displaying its language content
        """
        edit_url = get_object_edit_url(self.german, 'de')
        response = self.client.get(edit_url)

        # TODO check the language urls, you should be able to switch to the
        # preview of that...

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

    def test_toolbar_preview_mode_shows_correct_edit(self):
        """
        The edit button shows the correct url for the version that should be edited
        """
        preview_url = get_object_preview_url(self.german, 'de')
        version = self.german.versions.all().first()
        response = self.client.get(preview_url)

        toolbar = response.context['cms_toolbar']
        edit_button = toolbar.right_items[1].get_context()['buttons'][0]

        self.assertEqual(edit_button.name.lower(), 'editieren')
        self.assertIn('pagecontentversion/{}/edit-redirect/'.format(version.pk), edit_button.url)


class PublishedViewTests(CMSTestCase):
    """
    Testing that published and a draft version of already published is displayed
    correctly in different circumstances.
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
        self.published_content = 'content_v1'
        self.draft_content = 'content_v2'

        self.v1 = self.english.versions.all()[0]
        pl_en_v1 = self.english.get_placeholders()[0]
        add_plugin(pl_en_v1, 'TextPlugin', 'en', body=self.published_content)

        self.v1.publish(self.user)

        self.v2 = self.v1.copy(self.user)
        pl_en_v2 = self.v2.content.get_placeholders()[0]
        add_plugin(pl_en_v2, 'TextPlugin', 'en', body=self.draft_content)

        self.assertEqual(self.v2.state, DRAFT)

    def test_version_published_unauthenticated(self):
        """
        An unauthenticated user visits url and views only published content.
        """
        self.client.logout()
        url = self.english.get_absolute_url()
        response = self.client.get(url)

        self.assertContains(response, self.published_content)
        self.assertNotContains(response, self.draft_content)

    def test_version_published_authenticated(self):
        """
        An authenticated user visits url and views only published content.
        """

        url = self.english.get_absolute_url()
        response = self.client.get(url)

        self.assertContains(response, self.published_content)
        self.assertNotContains(response, self.draft_content)

    def test_preview_shows_published_content(self):
        """
        Authenticated user visits preview and sees the draft content.
        """
        pass

    def test_edit_url_view_draft_content(self):
        """
        Authenticated user visits edit url and see the draft content.
        """
        pass
