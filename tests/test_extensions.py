from unittest.mock import patch

from cms.extensions.extension_pool import ExtensionPool
from cms.test_utils.testcases import CMSTestCase
from cms.utils.urlutils import admin_reverse
from django.contrib import admin
from django.contrib.sites.models import Site
from django.test import RequestFactory

from djangocms_versioning.cms_config import copy_page_content
from djangocms_versioning.models import Version
from djangocms_versioning.test_utils.extended_polls.admin import (
    PollExtensionAdmin,
)
from djangocms_versioning.test_utils.extended_polls.models import (
    PollPageContentExtension,
)
from djangocms_versioning.test_utils.extensions.models import (
    TestPageContentExtension,
    TestPageExtension,
)
from djangocms_versioning.test_utils.factories import (
    PageContentFactory,
    PageVersionFactory,
    PollTitleExtensionFactory,
    TestTitleExtensionFactory,
)


class ExtensionTestCase(CMSTestCase):
    def setUp(self):
        self.version = PageVersionFactory(content__language="en")
        de_pagecontent = PageContentFactory(
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
            user=self.get_superuser(),
        )
        new_page_content = PageContentFactory(page=self.new_page, language="de")
        self.new_page.page_content_cache[de_pagecontent.language] = new_page_content

    def test_copy_extensions(self):
        """Try to copy the extension, without the monkeypatch this tests fails"""
        extension_pool = ExtensionPool()
        extension_pool.page_extensions = {TestPageExtension}
        extension_pool.title_extensions = {TestPageContentExtension}
        extension_pool.copy_extensions(
            self.page, self.new_page, languages=["de"]
        )
        # No asserts, this test originally failed because the versioned manager was called
        # in copy_extensions, now we call the original manager instead
        # https://github.com/divio/djangocms-versioning/pull/201/files#diff-fc33dd7b5aa9b1645545cf48dfc9b4ecR19

    def test_pagecontent_copy_method_creates_extension_title_extension_attached(self):
        """
        The page content copy method should create a new title extension, if one is attached to it.
        """
        page_content = self.version.content
        poll_extension = PollTitleExtensionFactory(extended_object=page_content)
        poll_extension.votes = 5
        poll_extension.save()

        with patch("cms.extensions.PageContentExtension.copy_relations") as mock:
            new_pagecontent = copy_page_content(page_content)

        mock.assert_called_once()
        self.assertNotEqual(new_pagecontent.pollpagecontentextension, poll_extension)
        self.assertEqual(page_content.pollpagecontentextension.pk, poll_extension.pk)
        self.assertNotEqual(page_content.pollpagecontentextension.pk, new_pagecontent.pollpagecontentextension.pk)
        self.assertEqual(new_pagecontent.pollpagecontentextension.votes, 5)
        self.assertEqual(PollPageContentExtension._base_manager.count(), 2)

    def test_pagecontent_copy_method_not_created_extension_title_extension_attached(self):
        """
        The pagecontent copy method should not create a new title extension, if one isn't attached to the pagecontent
        being copied
        """
        new_pagecontent = copy_page_content(self.version.content)

        self.assertFalse(hasattr(new_pagecontent, "polltitleextension"))
        self.assertEqual(PollPageContentExtension._base_manager.count(), 0)

    def test_pagecontent_copy_method_creates_extension_multiple_title_extension_attached(self):
        """
        The page content copy method should handle creation of multiple extensions
        """
        page_content = self.version.content
        poll_extension = PollTitleExtensionFactory(extended_object=page_content)
        poll_extension.votes = 5
        poll_extension.save()  # Needs to be in the db for copy method of core to work
        title_extension = TestTitleExtensionFactory(extended_object=page_content)

        new_pagecontent = copy_page_content(page_content)

        self.assertNotEqual(new_pagecontent.pollpagecontentextension, poll_extension)
        self.assertEqual(page_content.pollpagecontentextension.pk, poll_extension.pk)
        self.assertNotEqual(new_pagecontent.testpagecontentextension, poll_extension)
        self.assertEqual(page_content.testpagecontentextension.pk, poll_extension.pk)
        self.assertNotEqual(new_pagecontent.pollpagecontentextension, poll_extension)
        self.assertNotEqual(new_pagecontent.testpagecontentextension, title_extension)
        self.assertEqual(new_pagecontent.pollpagecontentextension.votes, 5)
        self.assertEqual(PollPageContentExtension._base_manager.count(), 2)
        self.assertEqual(TestPageContentExtension._base_manager.count(), 2)

    def test_title_extension_admin_monkey_patch_save(self):
        """
        When hitting the monkeypatched save method, with a draft pagecontent, ensure that we don't see failures
        due to versioning overriding monkeypatches
        """
        poll_extension = PollTitleExtensionFactory(extended_object=self.version.content)
        model_site = PollExtensionAdmin(admin_site=admin.AdminSite(), model=PollPageContentExtension)
        test_url = admin_reverse("extended_polls_pollpagecontentextension_change", args=(poll_extension.pk,))
        test_url += "?extended_object=%s" % self.version.content.pk
        request = RequestFactory().post(path=test_url)
        request.user = self.get_superuser()

        poll_extension.votes = 1
        model_site.save_model(request, poll_extension, form=None, change=False)

        self.assertEqual(PollPageContentExtension._base_manager.first().votes, 1)
        self.assertEqual(PollPageContentExtension._base_manager.count(), 1)

    def test_title_extension_admin_monkey_patch_save_date_modified_updated(self):
        """
        When making changes to an extended model that is attached to a PageContent via
        the Title Extension the date modified in a version should also be updated to reflect
        the correct date timestamp.
        """
        poll_extension = PollTitleExtensionFactory(extended_object=self.version.content)
        model_site = PollExtensionAdmin(admin_site=admin.AdminSite(), model=PollPageContentExtension)
        pre_changes_date_modified = Version.objects.get(id=self.version.pk).modified
        test_url = admin_reverse("extended_polls_pollpagecontentextension_change", args=(poll_extension.pk,))
        test_url += "?extended_object=%s" % self.version.content.pk

        request = RequestFactory().post(path=test_url)
        request.user = self.get_superuser()
        model_site.save_model(request, poll_extension, form=None, change=False)

        post_changes_date_modified = Version.objects.get(id=self.version.pk).modified

        self.assertNotEqual(pre_changes_date_modified, post_changes_date_modified)

    def test_title_extension_admin_monkeypatch_add_view(self):
        """
        When hitting the add view, without the monkeypatch, the pagecontent queryset will be filtered to only show
        published. Hit it with a draft, to make sure the monkeypatch works.
        """
        with self.login_user_context(self.get_superuser()):
            response = self.client.get(
                admin_reverse("extended_polls_pollpagecontentextension_add") +
                "?extended_object=%s" % self.version.content.pk,
                follow=True
            )
            self.assertEqual(response.status_code, 200)
