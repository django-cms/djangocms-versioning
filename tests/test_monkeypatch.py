from django.contrib.sites.models import Site

from cms.cms_toolbars import LANGUAGE_MENU_IDENTIFIER
from cms.extensions.extension_pool import ExtensionPool
from cms.test_utils.testcases import CMSTestCase
from cms.toolbar.toolbar import CMSToolbar
from cms.toolbar.utils import get_object_edit_url
from cms.utils.urlutils import admin_reverse

from djangocms_versioning.plugin_rendering import VersionContentRenderer
from djangocms_versioning.test_utils.extensions.models import (
    TestPageExtension,
    TestTitleExtension,
)
from djangocms_versioning.test_utils.factories import (
    PageContentFactory,
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

    def test_change_language_menu_page_toolbar(self):
        """Check that patched PageToolbar.change_language_menu only provide
        Add Translation links.
        """
        version = PageVersionFactory(content__language="en")
        PageContentFactory(page=version.content.page, language="de")
        page = version.content.page
        page.update_languages(["en", "de"])

        request = self.get_page_request(
            page=page,
            path=get_object_edit_url(version.content),
            user=self.get_superuser(),
        )
        request.toolbar.set_object(version.content)
        request.toolbar.populate()
        request.toolbar.post_template_populate()

        language_menu = request.toolbar.get_menu(LANGUAGE_MENU_IDENTIFIER)
        # 4 languages, Break, Add Translation menu
        self.assertEqual(language_menu.get_item_count(), 6)

        language_menu_dict = {
            menu.name: [item for item in menu.items]
            for key, menu in language_menu.menus.items()
        }
        self.assertIn("Add Translation", language_menu_dict.keys())
        self.assertNotIn("Delete Translation", language_menu_dict.keys())
        self.assertNotIn("Copy all plugins", language_menu_dict.keys())

        self.assertEquals(
            set([l.name for l in language_menu_dict["Add Translation"]]),
            set(["Française...", "Italiano..."]),
        )

        for item in language_menu_dict["Add Translation"]:
            self.assertIn(admin_reverse("cms_pagecontent_add"), item.url)
            self.assertIn("cms_page={}".format(page.pk), item.url)
            lang_code = "fr" if "Française" in item.name else "it"
            self.assertIn("language={}".format(lang_code), item.url)
