from cms.test_utils.testcases import CMSTestCase
from cms.toolbar.toolbar import CMSToolbar
from cms.utils.urlutils import admin_reverse

from djangocms_versioning.plugin_rendering import VersionContentRenderer
from djangocms_versioning.test_utils.factories import (
    PageFactory,
    PageVersionFactory,
    PlaceholderFactory,
    PollVersionFactory,
    TextPluginFactory,
)


class CMSToolbarTestCase(CMSTestCase):
    def test_content_renderer(self):
        """Test that cms.toolbar.toolbar.CMSToolbar.content_renderer
        is replaced with a property returning VersionContentRenderer
        """
        request = self.get_request("/")
        self.assertEqual(
            CMSToolbar(request).content_renderer.__class__, VersionContentRenderer
        )

    def test_cmstoolbar_mixin(self):
        from django.apps import apps

        from djangocms_versioning.cms_config import VersioningCMSConfig

        config = VersioningCMSConfig(apps)
        self.assertTrue(issubclass(config.cms_toolbar_mixin, object))


class PageContentAdminTestCase(CMSTestCase):

    def test_get_admin_model_object(self):
        """
        PageContent normally won't be able to fetch objects in draft. Test if the RequestToolbarForm
        finds objects in draft mode.
        """
        from cms.admin.forms import RequestToolbarForm
        version = PageVersionFactory()
        parameter = {
            "obj_id": version.object_id,
            "obj_type": f"{version.content_type.app_label}.{version.content_type.model}",
        }
        form = RequestToolbarForm(parameter)
        self.assertTrue(form.is_valid())

        data = form.clean()
        self.assertEqual(version.state, "draft")
        self.assertEqual(data["attached_obj"].pk, version.content.pk)

    def test_get_title_cache(self):
        """Check that patched Page._get_title_cache fills
        the title_cache with _prefetched_objects_cache data.
        """
        version = PageVersionFactory(content__language="en")
        page = version.content.page
        page._prefetched_objects_cache = {"pagecontent_set": [version.content]}

        page._get_page_content_cache(language="en", fallback=False, force_reload=False)
        self.assertEqual({"en": version.content}, page.page_content_cache)


class PageAdminCopyLanguageTestCase(CMSTestCase):

    def setUp(self):
        self.user = self.get_superuser()
        page = PageFactory()
        self.source_version = PageVersionFactory(content__page=page, content__language="en")
        self.target_version = PageVersionFactory(content__page=page, content__language="it")
        # Add default placeholders
        source_placeholder = PlaceholderFactory(source=self.source_version.content, slot="content")
        self.source_version.content.placeholders.add(source_placeholder)
        target_placeholder = PlaceholderFactory(source=self.target_version.content, slot="content")
        self.target_version.content.placeholders.add(target_placeholder)
        # Populate only the source placeholder as this is what we will be copying!
        TextPluginFactory(placeholder=source_placeholder)

        # Use the endpoint that the toolbar copy uses, this indirectly runs the monkey patched logic!
        # Simulating the user selecting in the Language menu "Copy all plugins" in the Versioned Page toolbar
        self.copy_url = admin_reverse("cms_pagecontent_copy_language", args=(self.source_version.content.pk,))
        self.copy_url_data = {
            "source_language": "en",
            "target_language": "it"
        }

    def test_page_copy_language_copies_source_draft_placeholder_plugins(self):
        """
        A draft pages contents are copied to a different language
        """
        with self.login_user_context(self.user):
            response = self.client.post(self.copy_url, self.copy_url_data)

        self.assertEqual(response.status_code, 200)

        original_plugins = self.source_version.content.placeholders.get().cmsplugin_set.all()
        new_plugins = self.target_version.content.placeholders.get().cmsplugin_set.all()

        self.assertEqual(new_plugins.count(), 1)
        self.assertNotEqual(new_plugins[0].pk, original_plugins[0].pk)
        self.assertNotEqual(new_plugins[0].language, original_plugins[0].language)
        self.assertEqual(new_plugins[0].language, "it")
        self.assertEqual(new_plugins[0].position, original_plugins[0].position)
        self.assertEqual(new_plugins[0].plugin_type, original_plugins[0].plugin_type)
        self.assertEqual(
            new_plugins[0].djangocms_text_ckeditor_text.body,
            original_plugins[0].djangocms_text_ckeditor_text.body,
        )

    def test_copy_language_copies_source_published_placeholder_plugins(self):
        """
        A published pages contents are copied to a different language
        """
        # Publish the source version
        self.source_version.publish(self.user)

        with self.login_user_context(self.user):
            response = self.client.post(self.copy_url, self.copy_url_data)

        self.assertEqual(response.status_code, 200)

        original_plugins = self.source_version.content.placeholders.get().cmsplugin_set.all()
        new_plugins = self.target_version.content.placeholders.get().cmsplugin_set.all()

        self.assertEqual(new_plugins.count(), 1)
        self.assertNotEqual(new_plugins[0].pk, original_plugins[0].pk)
        self.assertNotEqual(new_plugins[0].language, original_plugins[0].language)
        self.assertEqual(new_plugins[0].language, "it")
        self.assertEqual(new_plugins[0].position, original_plugins[0].position)
        self.assertEqual(new_plugins[0].plugin_type, original_plugins[0].plugin_type)
        self.assertEqual(
            new_plugins[0].djangocms_text_ckeditor_text.body,
            original_plugins[0].djangocms_text_ckeditor_text.body,
        )

    def test_copy_language_cannot_copy_to_published_version(self):
        """
        A pages contents cannot be copied to a published target version!
        """
        # Publish the target version
        self.target_version.publish(self.user)

        with self.login_user_context(self.user):
            response = self.client.post(self.copy_url, self.copy_url_data)

        # the Target version should be protected and we should not be allowed to copy any plugins to it!
        self.assertEqual(response.status_code, 403)

    def test_copy_language_copies_from_page_with_different_placeholders(self):
        """
        PageContents stores the template, this means that each PageContent can have
        a different template and placeholders. We should only copy plugins from common placeholders.

        This test contains different templates and a partially populated source and target placeholders.
        All plugins in the source should be left unnafected
        """
        source_placeholder_1 = PlaceholderFactory(source=self.source_version.content, slot="source_placeholder_1")
        self.source_version.content.placeholders.add(source_placeholder_1)
        TextPluginFactory(placeholder=source_placeholder_1)
        target_placeholder_1 = PlaceholderFactory(source=self.target_version.content, slot="target_placeholder_1")
        self.target_version.content.placeholders.add(target_placeholder_1)
        TextPluginFactory(placeholder=target_placeholder_1)

        self.source_version.publish(self.user)

        with self.login_user_context(self.user):
            response = self.client.post(self.copy_url, self.copy_url_data)

        self.assertEqual(response.status_code, 200)

        source_placeholder_different = self.source_version.content.placeholders.get(
            slot="source_placeholder_1").cmsplugin_set.all()
        target_placeholder_different = self.target_version.content.placeholders.get(
            slot="target_placeholder_1").cmsplugin_set.all()

        self.assertEqual(source_placeholder_different.count(), 1)
        self.assertEqual(target_placeholder_different.count(), 1)
        self.assertNotEqual(
            source_placeholder_different[0].djangocms_text_ckeditor_text.body,
            target_placeholder_different[0].djangocms_text_ckeditor_text.body
        )


class PageContentTreeViewTestCase(CMSTestCase):

    def test_default_cms_page_changelist_view_language_with_multi_language_content(self):
        """A multilingual page shows the correct values when
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


class WizzardTestCase(CMSTestCase):

    def test_success_url_for_cms_wizard(self):
        from cms.cms_wizards import cms_page_wizard, cms_subpage_wizard
        from cms.toolbar.utils import get_object_edit_url, get_object_preview_url

        from djangocms_versioning.test_utils.polls.cms_wizards import (
            poll_wizard,
        )

        # Test against page creations in different languages.
        version = PageVersionFactory(content__language="en")
        self.assertIn(
            cms_page_wizard.get_success_url(version.content.page, language="en"),
            [get_object_preview_url(version.content), get_object_edit_url(version.content)],
        )

        version = PageVersionFactory(content__language="en")
        self.assertIn(
            cms_subpage_wizard.get_success_url(version.content.page, language="en"),
            [get_object_preview_url(version.content), get_object_edit_url(version.content)],
        )

        version = PageVersionFactory(content__language="de")
        self.assertIn(
            cms_page_wizard.get_success_url(version.content.page, language="de"),
            [
                get_object_preview_url(version.content, language="de"),
                get_object_edit_url(version.content, language="de")
            ],
        )

        # Test against a model that doesn't have a PlaceholderRelationField
        version = PollVersionFactory()
        self.assertEqual(
            poll_wizard.get_success_url(version.content),
            version.content.get_absolute_url(),
        )
