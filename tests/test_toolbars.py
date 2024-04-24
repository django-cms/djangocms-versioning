from cms.cms_toolbars import LANGUAGE_MENU_IDENTIFIER, PlaceholderToolbar
from cms.test_utils.testcases import CMSTestCase
from cms.toolbar.utils import get_object_edit_url, get_object_preview_url
from cms.utils.urlutils import admin_reverse
from django.contrib.auth.models import Permission
from django.utils.text import slugify

from djangocms_versioning.cms_config import VersioningCMSConfig
from djangocms_versioning.constants import ARCHIVED, DRAFT, PUBLISHED
from djangocms_versioning.helpers import version_list_url
from djangocms_versioning.test_utils.factories import (
    BlogPostVersionFactory,
    FancyPollFactory,
    PageContentWithVersionFactory,
    PageUrlFactory,
    PageVersionFactory,
    PollVersionFactory,
    UserFactory,
)
from djangocms_versioning.test_utils.polls.cms_config import PollsCMSConfig
from djangocms_versioning.test_utils.test_helpers import (
    find_toolbar_buttons,
    get_toolbar,
    toolbar_button_exists,
)


class VersioningToolbarTestCase(CMSTestCase):
    def _get_publish_url(self, version, versionable=PollsCMSConfig.versioning[0]):
        """Helper method to return the expected publish url
        """
        admin_url = self.get_admin_url(
            versionable.version_model_proxy, "publish", version.pk
        )
        return admin_url

    def _get_edit_url(self, version, versionable=PollsCMSConfig.versioning[0]):
        """Helper method to return the expected edit redirect url
        """
        admin_url = self.get_admin_url(
            versionable.version_model_proxy, "edit_redirect", version.pk
        )
        return admin_url

    def _get_revert_url(self, version, versionable=PollsCMSConfig.versioning[0]):
        """Helper method to return the expected publish url
        """
        admin_url = self.get_admin_url(
            versionable.version_model_proxy, "revert", version.pk
        )
        return admin_url

    def test_publish_in_toolbar_in_edit_mode(self):
        """Test for Edit button in edit mode"""
        version = PollVersionFactory()
        toolbar = get_toolbar(version.content, edit_mode=True)

        toolbar.post_template_populate()
        revert_button = find_toolbar_buttons("Revert", toolbar.toolbar)
        self.assertListEqual(revert_button, [])  # No revert button

        publish_button = find_toolbar_buttons("Publish", toolbar.toolbar)[0]
        self.assertEqual(publish_button.name, "Publish")
        self.assertEqual(publish_button.url, self._get_publish_url(version))
        self.assertFalse(publish_button.disabled)
        self.assertListEqual(
            publish_button.extra_classes,
            ["cms-btn-action", "js-action", "cms-form-post-method", "cms-versioning-js-publish-btn"],
        )

    def test_revert_in_toolbar_in_preview_mode(self):
        """Test for Revert button outside mode"""

        version = PollVersionFactory()
        version.archive(self.get_superuser())
        toolbar = get_toolbar(version.content, edit_mode=False, user=self.get_superuser())

        toolbar.post_template_populate()
        publish_button = find_toolbar_buttons("Publish", toolbar.toolbar)
        self.assertListEqual(publish_button, [])  # No publish button

        revert_button = find_toolbar_buttons("Revert", toolbar.toolbar)[0]
        self.assertEqual(revert_button.name, "Revert")
        self.assertEqual(revert_button.url, self._get_revert_url(version))
        self.assertFalse(revert_button.disabled)
        self.assertListEqual(
            revert_button.extra_classes,
            ["cms-btn-action", ],
        )

    def test_publish_not_in_toolbar_in_preview_mode(self):
        version = PollVersionFactory()
        toolbar = get_toolbar(version.content, preview_mode=True)

        toolbar.post_template_populate()

        self.assertFalse(toolbar_button_exists("Publish", toolbar.toolbar))

    def test_publish_not_in_toolbar_in_structure_mode(self):
        version = PollVersionFactory()
        toolbar = get_toolbar(version.content, structure_mode=True)

        toolbar.post_template_populate()

        self.assertFalse(toolbar_button_exists("Publish", toolbar.toolbar))

    def test_dont_add_publish_for_models_not_registered_with_versioning(self):
        # User objects are not registered with versioning, so attempting
        # to populate a user toolbar should not attempt to add a publish
        # button
        toolbar = get_toolbar(UserFactory(), edit_mode=True)

        toolbar.post_template_populate()

        self.assertFalse(toolbar_button_exists("Publish", toolbar.toolbar))

    def test_url_for_publish_uses_version_id_not_content_id(self):
        """Regression test for a bug. Make sure than when we generate
        the publish url, we use the id of the version record, not the
        id of the content record.
        """
        # All versions are stored in the version table so increase the
        # id of version id sequence by creating a blogpost version
        BlogPostVersionFactory()
        # Now create a poll version - the poll content and version id
        # will be different.
        version = PollVersionFactory()
        toolbar = get_toolbar(
            version.content, user=self.get_superuser(), edit_mode=True
        )
        toolbar.post_template_populate()
        publish_button = find_toolbar_buttons("Publish", toolbar.toolbar)[0]

        self.assertEqual(publish_button.url, self._get_publish_url(version))

    def test_edit_in_toolbar_in_preview_mode(self):
        version = PageVersionFactory(content__template="")
        toolbar = get_toolbar(
            version.content, user=self.get_superuser(), preview_mode=True
        )

        toolbar.post_template_populate()
        edit_button = find_toolbar_buttons("Edit", toolbar.toolbar)[0]

        self.assertEqual(edit_button.name, "Edit")
        self.assertEqual(
            edit_button.url,
            self._get_edit_url(version, VersioningCMSConfig.versioning[0]),
        )
        self.assertFalse(edit_button.disabled)
        self.assertListEqual(
            edit_button.extra_classes,
            ["cms-btn-action", "js-action", "cms-form-post-method", "cms-versioning-js-edit-btn"]
        )

    def test_edit_not_in_toolbar_in_edit_mode(self):
        version = PollVersionFactory()
        toolbar = get_toolbar(
            version.content, user=self.get_superuser(), edit_mode=True
        )

        toolbar.post_template_populate()

        self.assertFalse(toolbar_button_exists("Edit", toolbar.toolbar))

    def test_edit_not_in_toolbar_in_structure_mode(self):
        version = PollVersionFactory()
        toolbar = get_toolbar(
            version.content, user=self.get_superuser(), structure_mode=True
        )

        toolbar.post_template_populate()

        self.assertFalse(toolbar_button_exists("Edit", toolbar.toolbar))

    def test_dont_add_edit_for_models_not_registered_with_versioning(self):
        # User objects are not registered with versioning, so attempting
        # to populate a user toolbar should not attempt to add a edit
        # button
        toolbar = get_toolbar(
            UserFactory(), user=self.get_superuser(), preview_mode=True
        )

        toolbar.post_template_populate()

        self.assertFalse(toolbar_button_exists("Edit", toolbar.toolbar))

    def test_url_for_edit_uses_version_id_not_content_id(self):
        """Regression test for a bug. Make sure than when we generate
        the edit url, we use the id of the version record, not the
        id of the content record.
        """
        # All versions are stored in the version table so increase the
        # id of version id sequence by creating a blogpost version
        BlogPostVersionFactory()
        # Now create a page version - the page content and version id
        # will be different.
        version = PageVersionFactory(content__template="")
        toolbar = get_toolbar(
            version.content, user=self.get_superuser(), preview_mode=True
        )
        edit_url = self._get_edit_url(version, VersioningCMSConfig.versioning[0])

        toolbar.post_template_populate()

        edit_button = find_toolbar_buttons("Edit", toolbar.toolbar)[0]
        self.assertEqual(edit_button.url, edit_url)

    def test_default_cms_edit_button_is_replaced_by_versioning_edit_button(self):
        """
        The versioning edit button is available on the toolbar
        when versioning is installed and the model is versionable.
        """
        page = PageVersionFactory(content__template="", content__language="en")
        url = get_object_preview_url(page.content)

        edit_url = self._get_edit_url(
            page, VersioningCMSConfig.versioning[0]
        )

        with self.login_user_context(self.get_superuser()):
            response = self.client.post(url)

        found_button_list = find_toolbar_buttons("Edit", response.wsgi_request.toolbar)
        # Only one edit button exists
        self.assertEqual(len(found_button_list), 1)
        # The only edit button that exists is the versioning button
        self.assertEqual(found_button_list[0].url, edit_url)

    def test_default_cms_edit_button_is_used_for_non_versioned_model(self):
        """
        The default cms edit button is present for a default model
        """
        unversionedpoll = FancyPollFactory()
        url = get_object_preview_url(unversionedpoll, language="en")
        edit_url = get_object_edit_url(unversionedpoll)

        with self.login_user_context(self.get_superuser()):
            response = self.client.post(url)

        found_button_list = find_toolbar_buttons("Edit", response.wsgi_request.toolbar)

        # Only one edit button exists
        self.assertEqual(len(found_button_list), 1)
        # The only edit button that exists is the standard cms button
        self.assertEqual(found_button_list[0].url, edit_url)

    def test_default_edit_button_from_cms_exists(self):
        """
        The default toolbar Edit button exists.
        """
        pagecontent = PageVersionFactory(content__template="")
        edit_url = self._get_edit_url(
            pagecontent.content, VersioningCMSConfig.versioning[0]
        )

        toolbar = get_toolbar(
            pagecontent.content,
            user=self.get_superuser(),
            toolbar_class=PlaceholderToolbar,
            preview_mode=True,
        )
        toolbar.post_template_populate()
        found_button_list = find_toolbar_buttons("Edit", toolbar.toolbar)

        # The only edit button that exists is the default cms button and not the versioning edit button
        self.assertEqual(len(found_button_list), 1)
        self.assertNotEqual(found_button_list[0].url, edit_url)

    def test_version_menu_for_non_version_content(self):
        # User objects are not registered with versioning, so attempting
        # to populate toolbar shouldn't contain a version menu
        toolbar = get_toolbar(UserFactory(), user=self.get_superuser(), edit_mode=True)
        toolbar.post_template_populate()
        version_menu = toolbar.toolbar.get_menu("version")
        self.assertIsNone(version_menu)

    def test_version_menu_for_version_content(self):
        # Versioned item should have versioning menu
        user = UserFactory(is_staff=True)
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="djangocms_versioning",
                codename="change_pollcontentversion",
            )
        )
        version = PollVersionFactory()
        toolbar = get_toolbar(version.content, user=user, preview_mode=True)
        toolbar.post_template_populate()
        version_menu = toolbar.toolbar.get_menu("version")
        self.assertEqual(version_menu.get_items()[0].name, "Manage Versions...")

    def test_version_menu_for_version_content_no_permission(self):
        """Manage versions entry shouldn't appear if user doesn't have
        access to that endpoint"""
        user = UserFactory(is_staff=True)
        version = PollVersionFactory()
        toolbar = get_toolbar(version.content, user=user, preview_mode=True)
        toolbar.post_template_populate()
        version_menu = toolbar.toolbar.get_menu("version")
        self.assertFalse(version_menu.get_items())

    def test_version_menu_for_none_version(self):
        # Version menu shouldnt be generated if version is None
        version = None
        toolbar = get_toolbar(version, user=self.get_superuser(), preview_mode=True)
        toolbar.post_template_populate()
        version_menu = toolbar.toolbar.get_menu("version")
        self.assertIsNone(version_menu)

    def test_version_menu_and_url_for_version_content(self):
        # Versioned item should have versioning menu and url should be version list url
        version = PollVersionFactory()
        toolbar = get_toolbar(
            version.content, user=self.get_superuser(), preview_mode=True
        )
        toolbar.post_template_populate()
        version_menu = toolbar.toolbar.get_menu("version")
        self.assertIsNotNone(version_menu)
        self.assertEqual(
            version_menu.get_items()[0].url, version_list_url(version.content)
        )

    def test_version_menu_label(self):
        # Versioned item should have correct version menu label
        from djangocms_versioning.constants import VERSION_STATES
        version = PollVersionFactory()
        toolbar = get_toolbar(
            version.content, user=self.get_superuser(), preview_mode=True
        )
        toolbar.post_template_populate()
        version_menu = toolbar.toolbar.get_menu("version")

        expected_label = f"Version #{version.number} ({dict(VERSION_STATES)[version.state]})"

        self.assertEqual(expected_label, version_menu.name)

    def test_view_published_in_toolbar_in_edit_mode_for_published_page(self):
        """
        The 'View Published' control is only relevant for pages that
        are published
        """
        published_version = PageVersionFactory(content__language="en", state=PUBLISHED)
        toolbar = get_toolbar(published_version.content, edit_mode=True)

        toolbar.post_template_populate()

        self.assertTrue(toolbar_button_exists("View Published", toolbar.toolbar))

    def test_view_published_in_toolbar_in_preview_mode_for_published_page(self):
        """
        The 'View Published' control is only relevant for pages that
        are published
        """
        published_version = PageVersionFactory(content__language="en", state=PUBLISHED)
        toolbar = get_toolbar(published_version.content, preview_mode=True)

        toolbar.post_template_populate()

        self.assertTrue(toolbar_button_exists("View Published", toolbar.toolbar))

    def test_view_published_not_in_toolbar_in_edit_mode_for_draft_page(self):
        """
        The 'View Published' control is only relevant for pages that
        are published
        """
        draft_version = PageVersionFactory(content__language="en")
        toolbar = get_toolbar(draft_version.content, edit_mode=True)

        toolbar.post_template_populate()

        self.assertFalse(toolbar_button_exists("View Published", toolbar.toolbar))

    def test_view_published_not_in_toolbar_in_preview_mode_for_draft_page(self):
        """
        The 'View Published' control is only relevant for pages that
        are published
        """
        draft_version = PageVersionFactory(content__language="en")
        toolbar = get_toolbar(draft_version.content, preview_mode=True)

        toolbar.post_template_populate()

        self.assertFalse(toolbar_button_exists("View Published", toolbar.toolbar))

    def test_view_published_not_in_toolbar_in_edit_mode_for_poll(self):
        """
        The 'View Published' toolbar control is only relevant for pages that have
        the concept of a live url / web viewable url with the toolbar
        """
        version = PollVersionFactory(state=PUBLISHED)
        toolbar = get_toolbar(version.content, edit_mode=True)

        toolbar.post_template_populate()

        self.assertFalse(toolbar_button_exists("View Published", toolbar.toolbar))

    def test_view_published_not_in_toolbar_in_preview_mode_for_poll(self):
        """
        The 'View Published' toolbar control is only relevant for pages that have
        the concept of a live url / web viewable url with the toolbar
        """
        version = PollVersionFactory(state=PUBLISHED)
        toolbar = get_toolbar(version.content, preview_mode=True)

        toolbar.post_template_populate()

        self.assertFalse(toolbar_button_exists("View Published", toolbar.toolbar))

    def test_view_published_in_toolbar_in_edit_mode_button_url(self):
        """
        The 'View Published' toolbar control url should be a valid
        live url when in the edit mode
        """
        published_version = PageVersionFactory(content__language="en")
        language = published_version.content.language
        PageUrlFactory(
            page=published_version.content.page,
            language=language,
            path=slugify("test_page"),
            slug=slugify("test_page"),
        )
        published_version.publish(user=self.get_superuser())
        draft_version = published_version.copy(self.get_superuser())
        edit_endpoint = get_object_edit_url(draft_version.content, language="en")
        expected_url = published_version.content.page.get_absolute_url(language=language)

        with self.login_user_context(self.get_superuser()):
            response = self.client.get(edit_endpoint)

        found_button_list = find_toolbar_buttons("View Published", response.wsgi_request.toolbar)

        # check only one View Published button exists
        self.assertEqual(len(found_button_list), 1)
        self.assertEqual(found_button_list[0].url, expected_url)

    def test_view_published_in_toolbar_in_preview_mode_button_url(self):
        """
        The 'View Published' toolbar control url should be a valid
        live url when in the preview mode
        """
        published_version = PageVersionFactory(content__language="en")
        language = published_version.content.language
        PageUrlFactory(
            page=published_version.content.page,
            language=language,
            path=slugify("test_page"),
            slug=slugify("test_page"),
        )
        published_version.publish(user=self.get_superuser())
        draft_version = published_version.copy(self.get_superuser())
        preview_endpoint = get_object_preview_url(draft_version.content, language="en")
        expected_url = published_version.content.page.get_absolute_url(language=language)

        with self.login_user_context(self.get_superuser()):
            response = self.client.get(preview_endpoint)

        found_button_list = find_toolbar_buttons("View Published", response.wsgi_request.toolbar)

        # check only one View Published button exists
        self.assertEqual(len(found_button_list), 1)
        self.assertEqual(found_button_list[0].url, expected_url)


class VersioningPageToolbarTestCase(CMSTestCase):

    def _get_toolbar_item_by_name(self, menu, name):
        for item in menu.items:
            if hasattr(item, "name") and item.name == name:
                return item
        return None

    def test_change_language_menu_page_toolbar(self):
        """Check that patched PageToolbar.change_language_menu only provides
        Add Translation links.
        """
        version = PageVersionFactory(content__language="en")
        PageContentWithVersionFactory(page=version.content.page, language="de")
        PageContentWithVersionFactory(page=version.content.page, language="it")
        page = version.content.page
        page.update_languages(["en", "de", "it"])

        request = self.get_page_request(
            page=page,
            path=get_object_edit_url(version.content),
            user=self.get_superuser(),
        )
        request.toolbar.set_object(version.content)
        request.toolbar.populate()
        request.toolbar.post_template_populate()

        language_menu = request.toolbar.get_menu(LANGUAGE_MENU_IDENTIFIER)
        # 3 out of 4 populated languages, Break, Add Translation menu, Copy all plugins
        self.assertEqual(language_menu.get_item_count(), 6)

        language_menu_dict = {
            menu.name: list(menu.items)
            for key, menu in language_menu.menus.items()
        }
        self.assertIn("Add Translation", language_menu_dict.keys())
        self.assertIn("Copy all plugins", language_menu_dict.keys())
        self.assertNotIn("Delete Translation", language_menu_dict.keys())

        self.assertEqual(
            {lang.name for lang in language_menu_dict["Add Translation"]},
            {"Française..."},
        )

        self.assertEqual(
            {lang.name for lang in language_menu_dict["Copy all plugins"]},
            {"from Italiano", "from Deutsche"},
        )

        for item in language_menu_dict["Add Translation"]:
            self.assertIn(admin_reverse("cms_pagecontent_add"), item.url)
            self.assertIn(f"cms_page={page.pk}", item.url)
            lang_code = "fr" if "Française" in item.name else "it"
            self.assertIn(f"language={lang_code}", item.url)

    def test_change_language_menu_page_toolbar_language_selector_version_link(self):
        """
        Ensure that the correct version is navigated to in the language selector.

        A real world scenario / issue seen:
            - Version 3: Draft
            - Version 2: Published
            - Version 1: Archived

        Version 1 was returned in the toolbar language selector which is incorrect,
        the latest version 4 should be returned.
        """
        superuser = self.get_superuser()
        en_pagecontent_1 = PageContentWithVersionFactory(language="en")
        page = en_pagecontent_1.page
        de_pagecontent_1 = PageContentWithVersionFactory(page=page, language="de")
        # Create remaining 3 versions for it
        it_pagecontent_1 = PageContentWithVersionFactory(page=page, language="it", version__state=ARCHIVED)
        it_pagecontent_1_version = it_pagecontent_1.versions.first()
        # Make version 1 archived by publishing the new version 2
        it_pagecontent_2 = PageContentWithVersionFactory(page=page, language="it", version__state=PUBLISHED)
        it_pagecontent_2_version = it_pagecontent_2.versions.first()
        # Create a new draft, which is what we expect to use
        it_pagecontent_3 = PageContentWithVersionFactory(page=page, language="it", version__state=DRAFT)
        it_pagecontent_3_version = it_pagecontent_3.versions.first()

        # Sanity check that all versions are int he state that we expect: Archived, Published, Draft
        self.assertEqual(it_pagecontent_1_version.state, ARCHIVED)
        self.assertEqual(it_pagecontent_2_version.state, PUBLISHED)
        self.assertEqual(it_pagecontent_3_version.state, DRAFT)

        page.update_languages(["en", "de", "it"])

        request = self.get_page_request(
            page=page,
            path=get_object_edit_url(en_pagecontent_1),
            user=superuser,
        )
        request.toolbar.set_object(en_pagecontent_1)
        request.toolbar.populate()
        request.toolbar.post_template_populate()

        language_menu = request.toolbar.get_menu(LANGUAGE_MENU_IDENTIFIER)
        language_menu_item_names = [item.name for item in language_menu.items if hasattr(item, "name")]

        self.assertIn("English", language_menu_item_names)
        self.assertIn("Deutsche", language_menu_item_names)
        self.assertIn("Italiano", language_menu_item_names)

        en_item = self._get_toolbar_item_by_name(language_menu, "English")
        en_preview_url = get_object_preview_url(en_pagecontent_1, "en")
        de_item = self._get_toolbar_item_by_name(language_menu, "Deutsche")
        de_preview_url = get_object_preview_url(de_pagecontent_1, "de")
        it_item = self._get_toolbar_item_by_name(language_menu, "Italiano")
        it_preview_url = get_object_preview_url(it_pagecontent_3, "it")

        # Ensure that each menu item points to the correct url
        self.assertEqual(en_item.url, en_preview_url)
        self.assertEqual(de_item.url, de_preview_url)
        self.assertEqual(it_item.url, it_preview_url)

    def test_page_toolbar_wo_language_menu(self):
        from django.utils.translation import gettext as _

        pagecontent = PageContentWithVersionFactory(language="en")
        page = pagecontent.page
        # Get request
        request = self.get_page_request(
            page=page,
            path=get_object_edit_url(pagecontent),
            user=self.get_superuser(),
        )
        # Remove language menu from request's toolbar
        del request.toolbar.menus[LANGUAGE_MENU_IDENTIFIER]

        # find VersioningPageToolbar
        for cls, toolbar in request.toolbar.toolbars.items():
            if cls == "djangocms_versioning.cms_toolbars.VersioningPageToolbar":
                # and call override_language_menu
                toolbar.override_language_menu()
                break

        language_menu = request.toolbar.get_menu(LANGUAGE_MENU_IDENTIFIER, _("Language"))
        self.assertIsNone(language_menu)
