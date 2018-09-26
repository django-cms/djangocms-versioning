from cms.test_utils.testcases import CMSTestCase
from cms.toolbar.toolbar import CMSToolbar

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
        from cms.cms_wizards import cms_page_wizard, cms_subpage_wizard
        from cms.toolbar.utils import get_object_preview_url

        from djangocms_versioning.test_utils.polls.cms_wizards import poll_wizard

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

        # Test against a model that doesn't have a PlaceholderRelationField
        version = PollVersionFactory()
        self.assertEqual(
            poll_wizard.get_success_url(version.content),
            version.content.get_absolute_url()
        )

    def test_get_title_cache(self):
        """Check that patched Page._get_title_cache fills
        the title_cache with _prefetched_objects_cache data.
        """
        version = PageVersionFactory(content__language='en')
        page = version.content.page
        page._prefetched_objects_cache = {'pagecontent_set': [version.content]}

        page._get_title_cache(language='en', fallback=False, force_reload=False)
        self.assertEqual({'en': version.content}, page.title_cache)
