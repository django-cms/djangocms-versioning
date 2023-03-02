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
)


class TestLatestAdminViewable(CMSTestCase):
    def test_extra_grouping_fields(self):
        page = PageFactory(node__depth=1)
        version = PageVersionFactory(
            content__page=page,
            content__language="en",
        )

        # Test 1: Try getting content w/o language grouping field => needs to fail
        self.assertRaises(ValueError, lambda: get_latest_admin_viewable_content(page))  # no language grouper

        # Test 2: Try getting content w/ langauge grouping field => needs to succeed
        content = get_latest_admin_viewable_content(page, language="en")  # OK
        self.assertEqual(content.versions.first(), version)

    def test_latest_admin_viewable_content(self):
        """The page content indicators render correctly"""
        page = PageFactory(node__depth=1)
        version1 = PageVersionFactory(
            content__page=page,
            content__language="en",
        )

        # New page has draft version, nothing else: latest_admin_viewable_content is draft
        content = get_latest_admin_viewable_content(page, language="en")
        self.assertEqual(content.versions.first(), version1)

        # Now archive
        version1.archive(user=self.get_superuser())
        # Archived version, nothing else: latest_admin_viewable_content is empty
        content = get_latest_admin_viewable_content(page, include_unpublished_archived=False, language="en")
        self.assertIsNone(content)
        # Archived version, nothing else: latest_admin_viewable_content is empty
        content = get_latest_admin_viewable_content(page, include_unpublished_archived=True, language="en")
        self.assertEqual(content.versions.first(), version1)

        # Now revert and publish => latest content is published
        version2 = version1.copy(created_by=self.get_superuser())
        version2.publish(user=self.get_superuser())
        # Published version is always viewable
        content = get_latest_admin_viewable_content(page, include_unpublished_archived=False, language="en")
        self.assertEqual(content.versions.first(), version2)
        # Published version is always viewable
        content = get_latest_admin_viewable_content(page, include_unpublished_archived=True, language="en")
        self.assertEqual(content.versions.first(), version2)

        # Now create a draft on top of published -> latest_admin_viewable content will be draft
        version3 = version2.copy(created_by=self.get_superuser())
        # Draft version is shadows published version
        content = get_latest_admin_viewable_content(page, include_unpublished_archived=False, language="en")
        self.assertEqual(content.versions.first(), version3)
        # Draft version is shadows published version
        content = get_latest_admin_viewable_content(page, include_unpublished_archived=True, language="en")
        self.assertEqual(content.versions.first(), version3)

        # Archive draft, with published version available
        version3.archive(user=self.get_superuser())
        # Published version now is the latest version
        content = get_latest_admin_viewable_content(page, include_unpublished_archived=False, language="en")
        self.assertEqual(content.versions.first(), version2)
        # Published version now is the latest version even when including archived
        content = get_latest_admin_viewable_content(page, include_unpublished_archived=True, language="en")
        self.assertEqual(content.versions.first(), version2)


class TestVersionState(CMSTestCase):
    def test_page_indicators(self):
        """Tests if the page content indicators render correctly"""
        page = PageFactory(node__depth=1)
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

            # Is unpublished indicator? No draft indicator
            response = self.client.get(page_tree, {"language": "en"})
            self.assertContains(response, "cms-pagetree-node-state-unpublished")
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
        """Test if IndicatorMixin causes the indicators to be rendered"""
        blogpost = BlogPostFactory()
        content = BlogContentFactory(
            blogpost=blogpost
        )
        BlogPostVersionFactory(
            content=content,
        )

        changelist = admin_reverse("blogpost_blogcontent_changelist")
        with self.login_user_context(self.get_superuser()):
            # New page ahs draft version, nothing else
            response = self.client.get(changelist)
            # Status indicator available?
            self.assertContains(response, "cms-pagetree-node-state-draft")
            self.assertNotContains(response, "cms-pagetree-node-state-published")
            self.assertNotContains(response, "cms-pagetree-node-state-dirty")
            # CSS loaded?
            self.assertContains(response, "cms.pagetree.css"),
            # JS loadeD?
            self.assertContains(response, "indicators.js")
