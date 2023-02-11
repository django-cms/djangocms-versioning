from cms.test_utils.testcases import CMSTestCase
from cms.utils.urlutils import admin_reverse

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


class TestVersionState(CMSTestCase):
    def test_page_indicators(self):
        page = PageFactory(node__depth=1)
        version1 = PageVersionFactory(
            content__page=page,
            content__language="en",
        )
        pk = version1.pk

        page_tree = admin_reverse("cms_pagecontent_get_tree")
        with self.login_user_context(self.get_superuser()):
            # New page ahs draft version, nothing else
            response = self.client.get(page_tree, {"language": "en"})
            self.assertNotContains(response, "cms-pagetree-node-state-empty")
            self.assertContains(response, "cms-pagetree-node-state-draft")
            self.assertNotContains(response, "cms-pagetree-node-state-published")
            self.assertNotContains(response, "cms-pagetree-node-state-dirty")
            self.assertNotContains(response, "cms-pagetree-node-state-unpublished")

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
        from django.contrib import admin

        admin = BlogContentAdmin(BlogContent, admin.site)
        self.assertIn("cms.pagetree.css", str(admin.media))
        self.assertIn("indicators.js", str(admin.media))

    def test_mixin_factory(self):
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
