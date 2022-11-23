from django.contrib import admin
from django.contrib.sites.models import Site
from django.test import RequestFactory

from cms.extensions.extension_pool import ExtensionPool
from cms.test_utils.testcases import CMSTestCase
from cms.utils.urlutils import admin_reverse

from djangocms_versioning.cms_config import copy_page_content
from djangocms_versioning.models import Version
from djangocms_versioning.test_utils.extended_polls.admin import PollExtensionAdmin
from djangocms_versioning.test_utils.extended_polls.models import PollTitleExtension
from djangocms_versioning.test_utils.extensions.models import (
    TestPageExtension,
    TestTitleExtension,
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
        )
        new_page_content = PageContentFactory(page=self.new_page, language='de')
        self.new_page.title_cache[de_pagecontent.language] = new_page_content

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

    def test_pagecontent_copy_method_creates_extension_title_extension_attached(self):
        """
        The page content copy method should create a new title extension, if one is attached to it.
        """
        page_content = self.version.content
        poll_extension = PollTitleExtensionFactory(extended_object=page_content)
        poll_extension.votes = 5

        new_pagecontent = copy_page_content(page_content)

        self.assertNotEqual(new_pagecontent.polltitleextension, poll_extension)
        self.assertEqual(page_content.polltitleextension.pk, poll_extension.pk)
        self.assertNotEqual(page_content.polltitleextension.pk, new_pagecontent.polltitleextension.pk)
        self.assertEqual(new_pagecontent.polltitleextension.votes, 5)
        self.assertEqual(PollTitleExtension._base_manager.count(), 2)

    def test_pagecontent_copy_method_not_created_extension_title_extension_attached(self):
        """
        The pagecontent copy method should not create a new title extension, if one isn't attached to the pagecontent
        being copied
        """
        new_pagecontent = copy_page_content(self.version.content)

        self.assertFalse(hasattr(new_pagecontent, "polltitleextension"))
        self.assertEqual(PollTitleExtension._base_manager.count(), 0)

    def test_pagecontent_copy_method_creates_extension_multiple_title_extension_attached(self):
        """
        The page content copy method should handle creation of multiple extensions
        """
        page_content = self.version.content
        poll_extension = PollTitleExtensionFactory(extended_object=page_content)
        poll_extension.votes = 5
        title_extension = TestTitleExtensionFactory(extended_object=page_content)

        new_pagecontent = copy_page_content(page_content)

        self.assertNotEqual(new_pagecontent.polltitleextension, poll_extension)
        self.assertEqual(page_content.polltitleextension.pk, poll_extension.pk)
        self.assertNotEqual(new_pagecontent.testtitleextension, poll_extension)
        self.assertEqual(page_content.testtitleextension.pk, poll_extension.pk)
        self.assertNotEqual(new_pagecontent.polltitleextension, poll_extension)
        self.assertNotEqual(new_pagecontent.testtitleextension, title_extension)
        self.assertEqual(new_pagecontent.polltitleextension.votes, 5)
        self.assertEqual(PollTitleExtension._base_manager.count(), 2)
        self.assertEqual(TestTitleExtension._base_manager.count(), 2)

    def test_title_extension_admin_monkey_patch_save(self):
        """
        When hitting the monkeypatched save method, with a draft pagecontent, ensure that we don't see failures
        due to versioning overriding monkeypatches
        """
        poll_extension = PollTitleExtensionFactory(extended_object=self.version.content)
        model_site = PollExtensionAdmin(admin_site=admin.AdminSite(), model=PollTitleExtension)
        test_url = admin_reverse("extended_polls_polltitleextension_change", args=(poll_extension.pk,))
        test_url += "?extended_object=%s" % self.version.content.pk
        request = RequestFactory().post(path=test_url)
        request.user = self.get_superuser()

        poll_extension.votes = 1
        model_site.save_model(request, poll_extension, form=None, change=False)

        self.assertEqual(PollTitleExtension.objects.first().votes, 1)
        self.assertEqual(PollTitleExtension.objects.count(), 1)

    def test_title_extension_admin_monkey_patch_save_date_modified_updated(self):
        """
        When making changes to an extended model that is attached to a PageContent via
        the Title Extension the date modified in a version should also be updated to reflect
        the correct date timestamp.
        """
        poll_extension = PollTitleExtensionFactory(extended_object=self.version.content)
        model_site = PollExtensionAdmin(admin_site=admin.AdminSite(), model=PollTitleExtension)
        pre_changes_date_modified = Version.objects.get(id=self.version.pk).modified
        test_url = admin_reverse("extended_polls_polltitleextension_change", args=(poll_extension.pk,))
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
                admin_reverse("extended_polls_polltitleextension_add") +
                "?extended_object=%s" % self.version.content.pk,
                follow=True
            )
            self.assertEqual(response.status_code, 200)

