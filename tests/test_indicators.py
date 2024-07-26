from cms.test_utils.testcases import CMSTestCase
from cms.utils.urlutils import admin_reverse

from djangocms_versioning.helpers import get_latest_admin_viewable_content
from djangocms_versioning.models import Version
from djangocms_versioning.test_utils.blogpost.admin import BlogContentAdmin
from djangocms_versioning.test_utils.blogpost.models import BlogContent
from djangocms_versioning.test_utils.factories import (
    BlogContentFactory,
    BlogPostFactory,
    BlogPostVersionFactory,
    PageFactory,
    PageVersionFactory,
    TreeNode,
)


class TestLatestAdminViewable(CMSTestCase):

    def setUp(self) -> None:
        """Creates a page, page content and a version object for the following tests"""
        self.page = PageFactory()
        self.version = PageVersionFactory(
            content__page=self.page,
            content__language="en",
        )

    def test_extra_grouping_fields(self):
        # Test 1: Try getting content w/o language grouping field => needs to fail
        self.assertRaises(ValueError, lambda: get_latest_admin_viewable_content(self.page))  # no language grouper

        # Test 2: Try getting content w/ langauge grouping field => needs to succeed
        content = get_latest_admin_viewable_content(self.page, language="en")  # OK
        self.assertEqual(content.versions.first(), self.version)

    def test_latest_admin_viewable_draft(self):
        # New page has draft version, nothing else: latest_admin_viewable_content is draft
        content = get_latest_admin_viewable_content(self.page, language="en")
        self.assertEqual(content.versions.first(), self.version)

    def test_latest_admin_viewable_archive(self):
        # First archive draft
        self.version.archive(user=self.get_superuser())
        # Archived version, nothing else: latest_admin_viewable_content is empty
        content = get_latest_admin_viewable_content(self.page, include_unpublished_archived=False, language="en")
        self.assertIsNone(content)
        # Archived version, nothing else: latest_admin_viewable_content is empty
        content = get_latest_admin_viewable_content(self.page, include_unpublished_archived=True, language="en")
        self.assertEqual(content.versions.first(), self.version)

    def test_latest_admin_viewable_published(self):
        # Now revert and publish => latest content is published
        self.version.archive(user=self.get_superuser())
        version2 = self.version.copy(created_by=self.get_superuser())
        version2.publish(user=self.get_superuser())
        # Published version is always viewable
        content = get_latest_admin_viewable_content(self.page, include_unpublished_archived=False, language="en")
        self.assertEqual(content.versions.first(), version2)
        # Published version is always viewable
        content = get_latest_admin_viewable_content(self.page, include_unpublished_archived=True, language="en")
        self.assertEqual(content.versions.first(), version2)

    def test_latest_admin_viewable_draft_on_top_of_published(self):
        # Now create a draft on top of published -> latest_admin_viewable content will be draft
        self.version.publish(user=self.get_superuser())
        version2 = self.version.copy(created_by=self.get_superuser())
        # Draft version is shadows published version
        content = get_latest_admin_viewable_content(self.page, include_unpublished_archived=False, language="en")
        self.assertEqual(content.versions.first(), version2)
        # Draft version is shadows published version
        content = get_latest_admin_viewable_content(self.page, include_unpublished_archived=True, language="en")
        self.assertEqual(content.versions.first(), version2)

    def test_latest_admin_viewable_archive_on_top_of_published(self):
        # Archive draft, with published version available
        self.version.publish(user=self.get_superuser())
        version2 = self.version.copy(created_by=self.get_superuser())
        version2.archive(user=self.get_superuser())
        # Published version now is the latest version
        content = get_latest_admin_viewable_content(self.page, include_unpublished_archived=False, language="en")
        self.assertEqual(content.versions.first(), self.version)
        # Published version now is the latest version even when including archived
        content = get_latest_admin_viewable_content(self.page, include_unpublished_archived=True, language="en")
        self.assertEqual(content.versions.first(), self.version)


class TestVersionState(CMSTestCase):
    def test_page_indicators(self):
        """The page content indicators render correctly"""
        page = PageFactory(node__depth=1) if TreeNode else PageFactory(depth=1)
        version1 = PageVersionFactory(
            content__page=page,
            content__language="en",
        )
        pk = version1.pk

        page_tree = admin_reverse("cms_pagecontent_get_tree")
        with self.login_user_context(self.get_superuser()):
            # New page has draft version, nothing else
            response = self.client.get(page_tree, {"language": "en"})
            self.assertNotContains(response, "cms-pagetree-node-state-empty")
            self.assertContains(response, "cms-pagetree-node-state-draft")
            self.assertNotContains(response, "cms-pagetree-node-state-published")
            self.assertNotContains(response, "cms-pagetree-node-state-dirty")
            self.assertNotContains(response, "cms-pagetree-node-state-unpublished")

            # Now archive
            response = self.client.post(admin_reverse("djangocms_versioning_pagecontentversion_archive",
                                                      args=(pk,)))
            self.assertEqual(response.status_code, 302)  # Sends a redirect
            # Is archived indicator? No draft indicator
            response = self.client.get(page_tree, {"language": "en"})
            self.assertContains(response, "cms-pagetree-node-state-archived")
            self.assertNotContains(response, "cms-pagetree-node-state-draft")

            # Now revert
            response = self.client.post(admin_reverse("djangocms_versioning_pagecontentversion_revert",
                                        args=(pk,)))
            self.assertEqual(response.status_code, 302)  # Sends a redirect
            # Is draft indicator? No archived indicator
            response = self.client.get(page_tree, {"language": "en"})
            self.assertContains(response, "cms-pagetree-node-state-draft")
            self.assertNotContains(response, "cms-pagetree-node-state-archived")
            # New draft was created, get new pk
            pk = Version.objects.filter_by_content_grouping_values(version1.content).order_by("-pk")[0].pk

            # Now publish
            response = self.client.post(admin_reverse("djangocms_versioning_pagecontentversion_publish",
                                        args=(pk,)))
            self.assertEqual(response.status_code, 302)  # Sends a redirect
            # Is published indicator? No draft indicator
            response = self.client.get(page_tree, {"language": "en"})
            self.assertContains(response, "cms-pagetree-node-state-published")
            self.assertNotContains(response, "cms-pagetree-node-state-draft")

            # Now unpublish
            response = self.client.post(admin_reverse("djangocms_versioning_pagecontentversion_unpublish",
                                        args=(pk,)))
            self.assertEqual(response.status_code, 302)  # Sends a redirect

            # Is unpublished indicator? No published indicator
            response = self.client.get(page_tree, {"language": "en"})
            self.assertContains(response, "cms-pagetree-node-state-unpublished")
            self.assertNotContains(response, "cms-pagetree-node-state-published")

            # Now revert
            response = self.client.post(admin_reverse("djangocms_versioning_pagecontentversion_revert",
                                        args=(pk,)))
            self.assertEqual(response.status_code, 302)  # Sends a redirect

            # Is draft indicator? No unpublished indicator
            response = self.client.get(page_tree, {"language": "en"})
            self.assertContains(response, "cms-pagetree-node-state-draft")
            self.assertNotContains(response, "cms-pagetree-node-state-unpublished")
            # New draft was created, get new pk
            pk = Version.objects.filter_by_content_grouping_values(version1.content).order_by("-pk")[0].pk

            # Now archive
            response = self.client.post(admin_reverse("djangocms_versioning_pagecontentversion_archive",
                                        args=(pk,)))
            self.assertEqual(response.status_code, 302)  # Sends a redirect

            # Is archived indicator? No draft indicator
            response = self.client.get(page_tree, {"language": "en"})
            self.assertContains(response, "cms-pagetree-node-state-archived")
            self.assertNotContains(response, "cms-pagetree-node-state-draft")

            # Now revert
            response = self.client.post(admin_reverse("djangocms_versioning_pagecontentversion_revert",
                                        args=(pk,)))
            self.assertEqual(response.status_code, 302)  # Sends a redirect

            # Is draft indicator? No unpublished indicator
            response = self.client.get(page_tree, {"language": "en"})
            self.assertContains(response, "cms-pagetree-node-state-draft")
            self.assertNotContains(response, "cms-pagetree-node-state-unpublished")
            # New draft was created, get new pk
            pk = Version.objects.filter_by_content_grouping_values(version1.content).order_by("-pk")[0].pk

            # Now publish again and then edit redirect to create a draft on top of published version
            response = self.client.post(admin_reverse("djangocms_versioning_pagecontentversion_publish",
                                                      args=(pk,)))
            self.assertEqual(response.status_code, 302)  # Sends a redirect
            response = self.client.post(admin_reverse("djangocms_versioning_pagecontentversion_edit_redirect",
                                                      args=(pk,)))
            self.assertEqual(response.status_code, 302)  # Sends a redirect

            # Is published indicator? No draft indicator
            response = self.client.get(page_tree, {"language": "en"})
            self.assertContains(response, "cms-pagetree-node-state-dirty")
            self.assertNotContains(response, "cms-pagetree-node-state-published")

    def test_mixin_facory_media(self):
        """Test if the IndicatorMixin imports required js and css"""
        from django.contrib import admin

        admin = BlogContentAdmin(BlogContent, admin.site)
        self.assertIn("cms.pagetree.css", str(admin.media))
        self.assertIn("indicators.js", str(admin.media))

    def test_mixin_factory(self):
        """The IndicatorMixin causes the indicators to be rendered"""
        blogpost = BlogPostFactory()
        content = BlogContentFactory(
            blogpost=blogpost
        )
        BlogPostVersionFactory(
            content=content,
        )

        changelist = admin_reverse("blogpost_blogcontent_changelist")
        with self.login_user_context(self.get_superuser()):
            # New page has draft version, nothing else
            response = self.client.get(changelist)
            # Status indicator available?
            self.assertContains(response, "cms-pagetree-node-state-draft")
            self.assertNotContains(response, "cms-pagetree-node-state-published")
            self.assertNotContains(response, "cms-pagetree-node-state-dirty")
            # CSS loaded?
            self.assertContains(response, "cms.pagetree.css"),
            # JS loadeD?
            self.assertContains(response, "indicators.js")

    def test_page_indicator_db_queries(self):
        """Only one query should be executed to get the indicator"""
        version = PageVersionFactory(
            content__language="en",
        )
        with self.assertNumQueries(1):
            from djangocms_versioning.indicators import content_indicator

            content_indicator(version.content)
