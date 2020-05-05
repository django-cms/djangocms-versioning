from django.contrib.sites.models import Site

from cms.extensions.extension_pool import ExtensionPool
from cms.models import PageContent
from cms.test_utils.testcases import CMSTestCase
from cms.toolbar.toolbar import CMSToolbar
from cms.utils.urlutils import admin_reverse

from djangocms_versioning.plugin_rendering import VersionContentRenderer
from djangocms_versioning.test_utils.extensions.models import (
    TestPageExtension,
    TestTitleExtension,
)
from djangocms_versioning.test_utils.factories import (
    PageContentFactory,
    PageFactory,
    PageVersionFactory,
    PollVersionFactory,
)


class MonkeypatchExtensionTestCase(CMSTestCase):
    def setUp(self):
        self.version = PageVersionFactory(content__language="en")
        pagecontent = PageContentFactory(
            page=self.version.content.page, language="de"
        )
        self.page = self.version.content.page
        site = Site.objects.first()
        self.new_page = self.page.copy(
            site=site,
            parent_node=self.page.node.parent,
            translations=False,
            permissions=False,
            extensions=False,
        )
        new_page_content = PageContentFactory(page=self.new_page, language='de')
        self.new_page.title_cache[pagecontent.language] = new_page_content

    def test_copy_extensions(self):
        """Try to copy the extension, without the monkeypatch this tests fails"""
        extension_pool = ExtensionPool()
        extension_pool.page_extensions = set([TestPageExtension])
        extension_pool.title_extensions = set([TestTitleExtension])
        extension_pool.copy_extensions(
            self.page, self.new_page, languages=['de']
        )
        # No asserts, this test originally failed because the versioned manager was called
        # in copy_extensions, now we call the original manager instead
        # https://github.com/divio/djangocms-versioning/pull/201/files#diff-fc33dd7b5aa9b1645545cf48dfc9b4ecR19


class MonkeypatchTestCase(CMSTestCase):
    def test_content_renderer(self):
        """Test that cms.toolbar.toolbar.CMSToolbar.content_renderer
        is replaced with a property returning VersionContentRenderer
        """
        request = self.get_request("/")
        self.assertEqual(
            CMSToolbar(request).content_renderer.__class__, VersionContentRenderer
        )

    def test_get_admin_model_object(self):
        """
        PageContent normally won't be able to fetch objects in draft.
        With the mocked get_admin_model_object_by_id it is able to fetch objects
        in draft mode.
        """
        from cms.utils.helpers import get_admin_model_object_by_id

        version = PageVersionFactory()
        content = get_admin_model_object_by_id(PageContent, version.content.pk)

        self.assertEqual(version.state, 'draft')
        self.assertEqual(content.pk, version.content.pk)

    def test_success_url_for_cms_wizard(self):
        from cms.cms_wizards import cms_page_wizard, cms_subpage_wizard
        from cms.toolbar.utils import get_object_preview_url

        from djangocms_versioning.test_utils.polls.cms_wizards import poll_wizard

        # Test against page creations in different languages.
        version = PageVersionFactory(content__language="en")
        self.assertEqual(
            cms_page_wizard.get_success_url(version.content.page, language="en"),
            get_object_preview_url(version.content),
        )

        version = PageVersionFactory(content__language="en")
        self.assertEqual(
            cms_subpage_wizard.get_success_url(version.content.page, language="en"),
            get_object_preview_url(version.content),
        )

        version = PageVersionFactory(content__language="de")
        self.assertEqual(
            cms_page_wizard.get_success_url(version.content.page, language="de"),
            get_object_preview_url(version.content, language="de"),
        )

        # Test against a model that doesn't have a PlaceholderRelationField
        version = PollVersionFactory()
        self.assertEqual(
            poll_wizard.get_success_url(version.content),
            version.content.get_absolute_url(),
        )

    def test_get_title_cache(self):
        """Check that patched Page._get_title_cache fills
        the title_cache with _prefetched_objects_cache data.
        """
        version = PageVersionFactory(content__language="en")
        page = version.content.page
        page._prefetched_objects_cache = {"pagecontent_set": [version.content]}

        page._get_title_cache(language="en", fallback=False, force_reload=False)
        self.assertEqual({"en": version.content}, page.title_cache)


class MonkeypatchAdminTestCase(CMSTestCase):

    def test_default_cms_page_changelist_view_language_with_multi_language_content(self):
        """A multi lingual page shows the correct values when
        language filters / additional grouping values are set
        using the default CMS PageContent view
        """
        page = PageFactory(node__depth=1)
        en_version1 = PageVersionFactory(
            content__page=page,
            content__language="en",
        )
        fr_version1 = PageVersionFactory(
            content__page=page,
            content__language="fr",
        )

        # Use the tree endpoint which is what the pagecontent changelist depends on
        changelist_url = admin_reverse("cms_pagecontent_get_tree")
        with self.login_user_context(self.get_superuser()):
            en_response = self.client.get(changelist_url, {"language": "en"})
            fr_response = self.client.get(changelist_url, {"language": "fr"})

        # English values are only returned
        self.assertEqual(200, en_response.status_code)
        self.assertContains(en_response, en_version1.content.title)
        self.assertNotContains(en_response, fr_version1.content.title)

        # French values are only returned
        self.assertEqual(200, fr_response.status_code)
        self.assertContains(fr_response, fr_version1.content.title)
        self.assertNotContains(fr_response, en_version1.content.title)
