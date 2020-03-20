from unittest.mock import patch

import django
from django.contrib import admin
from django.contrib.sites.models import Site

from cms.api import add_plugin
from cms.models import PageContent, PageUrl
from cms.test_utils.testcases import CMSTestCase
from cms.utils.plugins import downcast_plugins

from djangocms_versioning.test_utils.factories import (
    PageContentWithVersionFactory,
    PlaceholderFactory,
)


version = list(map(int, django.__version__.split('.')))
GTE_DJ20 = version[0] >= 2


class PageContentAdminTestCase(CMSTestCase):
    def setUp(self):
        self.modeladmin = admin.site._registry[PageContent]

    def test_duplicate_url_is_replaced(self):
        """
        The old url /duplicate/ has been removed. But cms_pagecontent_duplicate
        still exists.
        """

        urls = self.modeladmin.get_urls()
        if GTE_DJ20:
            duplicate_url = [u for u in urls if '/duplicate/' in u.pattern.regex.pattern]
        else:
            duplicate_url = [u for u in urls if '/duplicate/' in u.regex.pattern]
        name_url = [u for u in urls if 'cms_pagecontent_duplicate' == u.name]

        self.assertEqual(len(duplicate_url), 0)
        self.assertEqual(len(name_url), 1)


class DuplicateViewTestCase(CMSTestCase):
    def test_obj_does_not_exist(self):
        with self.login_user_context(self.get_superuser()), patch(
            "django.contrib.messages.add_message"
        ) as mock:
            response = self.client.get(
                self.get_admin_url(PageContent, "duplicate", "foo")
            )

        self.assertRedirects(response, "/en/admin/", target_status_code=302)
        self.assertEqual(mock.call_count, 1)
        self.assertEqual(mock.call_args[0][1], 30)  # warning level
        self.assertEqual(
            mock.call_args[0][2],
            'page content with ID "foo" doesn\'t exist. Perhaps it was deleted?',
        )

    def test_get(self):
        pagecontent = PageContentWithVersionFactory()
        with self.login_user_context(self.get_superuser()):
            response = self.client.get(
                self.get_admin_url(PageContent, "duplicate", pagecontent.pk)
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PageContent._base_manager.count(), 1)

    def test_post_empty_slug(self):
        pagecontent = PageContentWithVersionFactory()

        with self.login_user_context(self.get_superuser()):
            response = self.client.post(
                self.get_admin_url(PageContent, "duplicate", pagecontent.pk),
                data={"slug": ""},
            )
            form = response.context["form"]

        self.assertEqual(response.status_code, 200)
        self.assertFalse(form.is_valid())
        self.assertIn("slug", form.errors)
        self.assertEqual(form.errors["slug"], ["This field is required."])

    def test_post_empty_slug_after_slugify(self):
        pagecontent = PageContentWithVersionFactory()

        with self.login_user_context(self.get_superuser()):
            response = self.client.post(
                self.get_admin_url(PageContent, "duplicate", pagecontent.pk),
                data={"site": Site.objects.first().pk, "slug": "£"},
            )
            form = response.context["form"]

        self.assertEqual(response.status_code, 200)
        self.assertFalse(form.is_valid())
        self.assertIn("slug", form.errors)
        self.assertEqual(form.errors["slug"], ["Slug must not be empty."])

    def test_post(self):
        """the slot for content is always there, the slot for navigation needs
        to be created"""
        pagecontent = PageContentWithVersionFactory(template="page.html")
        placeholder = PlaceholderFactory(slot="content", source=pagecontent)
        PlaceholderFactory(slot="navigation", source=pagecontent)
        add_plugin(placeholder, "TextPlugin", pagecontent.language, body="Test text")

        with self.login_user_context(self.get_superuser()):
            response = self.client.post(
                self.get_admin_url(PageContent, "duplicate", pagecontent.pk),
                data={"site": Site.objects.first().pk, "slug": "foo bar"},
                follow=True,
            )

        self.assertRedirects(response, self.get_admin_url(PageContent, "changelist"))
        new_pagecontent = PageContent._base_manager.latest("pk")
        new_placeholder = new_pagecontent.placeholders.get(slot="content")
        self.assertEqual(PageContent._base_manager.count(), 2)
        self.assertNotEqual(pagecontent, new_pagecontent)
        self.assertNotEqual(pagecontent.page, new_pagecontent.page)
        self.assertEqual(pagecontent.language, new_pagecontent.language)
        self.assertEqual(
            new_pagecontent.page.get_slug(new_pagecontent.language), "foo-bar"
        )
        new_plugins = list(downcast_plugins(new_placeholder.get_plugins_list()))

        self.assertEqual(len(new_plugins), 1)
        self.assertEqual(new_plugins[0].plugin_type, "TextPlugin")
        self.assertEqual(new_plugins[0].body, "Test text")

    def test_post_with_parent(self):
        pagecontent1 = PageContentWithVersionFactory(
            template="page.html",
            page__node__depth=0,
            page__node__path="0001",
            page__node__numchild=1,
        )
        PageUrl.objects.create(
            slug="foo",
            path="foo",
            language=pagecontent1.language,
            page=pagecontent1.page,
        )
        pagecontent2 = PageContentWithVersionFactory(
            template="page.html",
            language=pagecontent1.language,
            page__node__parent_id=pagecontent1.page.node_id,
            page__node__depth=1,
            page__node__path="00010001",
        )
        placeholder = PlaceholderFactory(slot="content", source=pagecontent2)
        add_plugin(placeholder, "TextPlugin", pagecontent2.language, body="Test text")

        with self.login_user_context(self.get_superuser()):
            response = self.client.post(
                self.get_admin_url(PageContent, "duplicate", pagecontent2.pk),
                data={"site": Site.objects.first().pk, "slug": "bar"},
                follow=True,
            )

        self.assertRedirects(response, self.get_admin_url(PageContent, "changelist"))
        new_pagecontent = PageContent._base_manager.latest("pk")
        new_placeholder = new_pagecontent.placeholders.get(slot="content")
        self.assertEqual(PageContent._base_manager.count(), 3)
        self.assertNotEqual(pagecontent2, new_pagecontent)
        self.assertNotEqual(pagecontent2.page, new_pagecontent.page)
        self.assertEqual(pagecontent2.language, new_pagecontent.language)
        self.assertEqual(
            new_pagecontent.page.get_path(new_pagecontent.language), "foo/bar"
        )
        new_plugins = list(downcast_plugins(new_placeholder.get_plugins_list()))
        self.assertEqual(len(new_plugins), 1)
        self.assertEqual(new_plugins[0].plugin_type, "TextPlugin")
        self.assertEqual(new_plugins[0].body, "Test text")
