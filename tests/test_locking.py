from unittest import skip

from django.contrib import admin
from django.template.loader import render_to_string
from django.test import RequestFactory, override_settings
from django.utils.translation import gettext_lazy as _

from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning import admin as versioning_admin
from djangocms_versioning.constants import DRAFT, PUBLISHED
from djangocms_versioning.helpers import create_version_lock, version_list_url, version_is_unlocked_for_user
from djangocms_versioning.models import Version
from djangocms_versioning.test_utils import factories

from djangocms_versioning import conf
from djangocms_versioning.test_utils.polls import admin as polls_admin
from djangocms_versioning.test_utils.polls.cms_config import PollsCMSConfig


@override_settings(DJANGOCMS_VERSIONING_LOCK_VERSIONS=True)
class AdminLockedFieldTestCase(CMSTestCase):

    def setUp(self):
        import importlib
        importlib.reload(conf)
        importlib.reload(versioning_admin)

        site = admin.AdminSite()
        self.hijacked_admin = versioning_admin.VersionAdmin(Version, site)

    def test_version_admin_contains_locked_field(self):
        """
        The locked column exists in the admin field list
        """
        request = RequestFactory().get('/admin/djangocms_versioning/pollcontentversion/')
        self.assertIn(_("locked"), self.hijacked_admin.get_list_display(request))

    def test_version_lock_state_locked(self):
        """
        A published version does not have an entry in the locked column in the admin
        """
        published_version = factories.PollVersionFactory(state=PUBLISHED)

        self.assertEqual("", self.hijacked_admin.locked(published_version))

    def test_version_lock_state_unlocked(self):
        """
        A locked draft version does have an entry in the locked column in the version
        admin and is not empty
        """
        draft_version = factories.PollVersionFactory(state=DRAFT)
        create_version_lock(draft_version, self.get_superuser())

        self.assertNotEqual("", self.hijacked_admin.locked(draft_version))


@override_settings(DJANGOCMS_VERSIONING_LOCK_VERSIONS=True)
class AdminPermissionTestCase(CMSTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.versionable = PollsCMSConfig.versioning[0]

    def setUp(self):
        import importlib
        importlib.reload(conf)
        importlib.reload(versioning_admin)

        self.superuser = self.get_superuser()
        self.user_has_change_perms = self._create_user(
            "user_has_unlock_perms",
            is_staff=True,
            permissions=["change_pollcontentversion", "delete_versionlock"],
        )

    def test_user_has_change_permission(self):
        """
        The user who created the version has permission to change it
        """
        version = factories.PollVersionFactory(
            state=DRAFT,
            created_by=self.user_has_change_perms,
            locked_by=self.user_has_change_perms,
        )
        url = self.get_admin_url(self.versionable.content_model, 'change', version.content.pk)

        with self.login_user_context(self.user_has_change_perms):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_user_does_not_have_change_permission(self):
        """
        A different user from the user who created
        the version does not have permission to change it
        """
        author = factories.UserFactory(is_staff=True)
        version = factories.PollVersionFactory(state=DRAFT, created_by=author, locked_by=author)

        url = self.get_admin_url(self.versionable.content_model, 'change', version.content.pk)
        with self.login_user_context(self.user_has_change_perms):
            response = self.client.get(url)

        self.assertIsNotNone(version.locked_by)  # Was locked
        self.assertEqual(response.status_code, 403)


@override_settings(DJANGOCMS_VERSIONING_LOCK_VERSIONS=True)
class VersionLockUnlockTestCase(CMSTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.versionable = PollsCMSConfig.versioning[0]
        cls.default_permissions = ["change_pollcontentversion"]

    def setUp(self):
        import importlib
        importlib.reload(conf)
        importlib.reload(versioning_admin)

        self.superuser = self.get_superuser()
        self.user_author = self._create_user(
            "author",
            is_staff=True,
            permissions=self.default_permissions,
        )
        self.user_has_no_unlock_perms = self._create_user(
            "user_has_no_unlock_perms",
            is_staff=True,
            permissions=self.default_permissions,
        )
        self.user_has_unlock_perms = self._create_user(
            "user_has_unlock_perms",
            is_staff=True,
            permissions=["delete_versionlock"] + self.default_permissions,
        )

    def test_unlock_view_redirects_404_when_not_draft(self):
        poll_version = factories.PollVersionFactory(
            state=PUBLISHED,
            created_by=self.superuser,
            locked_by=self.superuser,
        )
        unlock_url = self.get_admin_url(self.versionable.version_model_proxy, 'unlock', poll_version.pk)

        # 404 when not in draft
        with self.login_user_context(self.superuser):
            response = self.client.post(unlock_url, follow=True)

        self.assertEqual(response.status_code, 404)

    def test_unlock_view_not_possible_for_user_with_no_permissions(self):
        poll_version = factories.PollVersionFactory(
            state=DRAFT,
            created_by=self.user_author,
            locked_by=self.user_author,
        )
        unlock_url = self.get_admin_url(self.versionable.version_model_proxy, 'unlock', poll_version.pk)

        with self.login_user_context(self.user_has_no_unlock_perms):
            response = self.client.post(unlock_url, follow=True)

        self.assertEqual(response.status_code, 403)

        # Fetch the latest state of this version
        updated_poll_version = Version.objects.get(pk=poll_version.pk)

        # The version is still locked
        self.assertIsNotNone(updated_poll_version.locked_by)
        # The author is unchanged
        self.assertEqual(updated_poll_version.locked_by, self.user_author)

    def test_unlock_view_possible_for_user_with_permissions(self):
        poll_version = factories.PollVersionFactory(
            state=DRAFT,
            created_by=self.user_author,
            locked_by=self.user_author
        )
        unlock_url = self.get_admin_url(self.versionable.version_model_proxy, 'unlock', poll_version.pk)

        with self.login_user_context(self.user_has_unlock_perms):
            response = self.client.post(unlock_url, follow=True)

        self.assertEqual(response.status_code, 200)

        # Fetch the latest state of this version
        updated_poll_version = Version.objects.get(pk=poll_version.pk)

        # The version is not locked
        self.assertFalse(hasattr(updated_poll_version, 'versionlock'))

    @skip("Requires clarification if this is still a valid requirement!")
    def test_unlock_link_not_present_for_author(self):
        # FIXME: May be redundant now as this requirement was probably removed at a later date due
        #  to the fact that an author may be asked to unlock their version for someone else to use!
        author = self.get_superuser()
        poll_version = factories.PollVersionFactory(state=DRAFT, created_by=author, locked_by=author)
        changelist_url = version_list_url(poll_version.content)
        unlock_url = self.get_admin_url(self.versionable.version_model_proxy, 'unlock', poll_version.pk)
        unlock_control = render_to_string(
            'djangocms_version_locking/admin/unlock_icon.html',
            {'unlock_url': unlock_url}
        )

        with self.login_user_context(author):
            response = self.client.get(changelist_url)

        self.assertNotContains(response, unlock_control, html=True)

    def test_unlock_link_not_present_for_user_with_no_unlock_privileges(self):
        poll_version = factories.PollVersionFactory(
            state=DRAFT,
            created_by=self.user_author,
            locked_by=self.user_author)
        changelist_url = version_list_url(poll_version.content)
        unlock_url = self.get_admin_url(self.versionable.version_model_proxy, 'unlock', poll_version.pk)

        with self.login_user_context(self.user_has_no_unlock_perms):
            response = self.client.post(changelist_url)

        self.assertNotContains(response, unlock_url)

    def test_unlock_link_present_for_user_with_privileges(self):
        poll_version = factories.PollVersionFactory(
            state=DRAFT,
            created_by=self.user_author,
            locked_by=self.user_author,
        )
        changelist_url = version_list_url(poll_version.content)
        unlock_url = self.get_admin_url(self.versionable.version_model_proxy, 'unlock', poll_version.pk)
        unlock_control = "cms-action-unlock"

        with self.login_user_context(self.user_has_unlock_perms):
            response = self.client.post(changelist_url)

        self.assertContains(response, unlock_control)  # Action button present
        self.assertContains(response, unlock_url)  # Not present for disabled action button

    def test_unlock_link_only_present_for_draft_versions(self):
        draft_version = factories.PollVersionFactory(created_by=self.user_author, locked_by=self.user_author)
        published_version = Version.objects.create(
            content=factories.PollContentFactory(poll=draft_version.content.poll),
            created_by=factories.UserFactory(),
            state=PUBLISHED
        )
        draft_unlock_url = self.get_admin_url(self.versionable.version_model_proxy, 'unlock', draft_version.pk)
        draft_unlock_control = "cms-action-unlock"
        published_unlock_url = self.get_admin_url(self.versionable.version_model_proxy, 'unlock', published_version.pk)
        published_unlock_control = "cms-action-unlock"
        changelist_url = version_list_url(draft_version.content)

        with self.login_user_context(self.superuser):
            response = self.client.post(changelist_url)

        # The draft version unlock control exists
        self.assertContains(response, draft_unlock_control)
        self.assertContains(response, draft_unlock_url)
        # The published version exists
        self.assertContains(response, published_unlock_control)
        self.assertNotContains(response, published_unlock_url)

    def test_unlock_and_new_user_edit_creates_version_lock(self):
        """
        When a version is unlocked a different user (or the same) can then visit the edit link and take
        ownership of the version, this creates a version lock for the editing user
        """
        draft_version = factories.PollVersionFactory(created_by=self.user_author, locked_by=self.user_author)
        draft_unlock_url = self.get_admin_url(self.versionable.version_model_proxy,
                                              'unlock', draft_version.pk)

        # The version is owned by the author
        self.assertEqual(draft_version.created_by, self.user_author)
        # The version lock exists and is owned by the author
        self.assertEqual(draft_version.locked_by, self.user_author)

        # Unlock the version with a different user with unlock permissions
        with self.login_user_context(self.user_has_unlock_perms):
            self.client.post(draft_unlock_url, follow=True)

        updated_draft_version = Version.objects.get(pk=draft_version.pk)
        updated_draft_edit_url = self.get_admin_url(
            self.versionable.version_model_proxy,
            'edit_redirect', updated_draft_version.pk
        )

        # The version is still owned by the author
        self.assertTrue(updated_draft_version.created_by, self.user_author)
        # The version lock does not exist
        self.assertFalse(hasattr(updated_draft_version, 'versionlock'))

        # Visit the edit page with a user without unlock permissions
        with self.login_user_context(self.user_has_no_unlock_perms):
            self.client.post(updated_draft_edit_url)

        updated_draft_version = Version.objects.get(pk=draft_version.pk)

        # The version is now owned by the user with no permissions
        self.assertTrue(updated_draft_version.created_by, self.user_has_no_unlock_perms)
        # The version lock exists and is now owned by the user with no permissions
        self.assertEqual(updated_draft_version.locked_by, self.user_has_no_unlock_perms)


@override_settings(DJANGOCMS_VERSIONING_LOCK_VERSIONS=True)
class VersionLockEditActionStateTestCase(CMSTestCase):

    def setUp(self):
        import importlib
        importlib.reload(conf)
        importlib.reload(versioning_admin)

        self.superuser = self.get_superuser()
        self.user_author = self._create_user("author", is_staff=True, is_superuser=False)
        self.versionable = PollsCMSConfig.versioning[0]
        self.version_admin = admin.site._registry[self.versionable.version_model_proxy]

    def test_edit_action_link_enabled_state(self):
        """
        The edit action is active
        """
        version = factories.PollVersionFactory(created_by=self.user_author, locked_by=self.user_author)
        author_request = RequestFactory()
        author_request.user = self.user_author
        otheruser_request = RequestFactory()
        otheruser_request.user = self.superuser

        actual_enabled_state = self.version_admin._get_edit_link(version, author_request)

        self.assertNotIn("inactive", actual_enabled_state)

    def test_edit_action_link_disabled_state(self):
        """
        The edit action is disabled for a different user to the locked user
        """
        version = factories.PollVersionFactory(created_by=self.user_author, locked_by=self.user_author)
        author_request = RequestFactory()
        author_request.user = self.user_author
        otheruser_request = RequestFactory()
        otheruser_request.user = self.superuser

        actual_disabled_state = self.version_admin._get_edit_link(version, otheruser_request)

        self.assertFalse(version.check_edit_redirect.as_bool(self.superuser))
        self.assertEqual("", actual_disabled_state)


@override_settings(DJANGOCMS_VERSIONING_LOCK_VERSIONS=True)
class VersionLockEditActionSideFrameTestCase(CMSTestCase):
    def setUp(self):
        import importlib
        importlib.reload(conf)
        importlib.reload(versioning_admin)

        self.superuser = self.get_superuser()
        self.user_author = self._create_user("author", is_staff=True, is_superuser=False)
        self.versionable = PollsCMSConfig.versioning[0]
        self.version_admin = admin.site._registry[self.versionable.version_model_proxy]

    def test_version_unlock_keep_side_frame(self):
        """
        When clicking on an versionables enabled unlock icon, the sideframe is kept open
        """
        version = factories.PollVersionFactory(created_by=self.user_author, locked_by=self.user_author)
        author_request = RequestFactory()
        author_request.user = self.user_author
        otheruser_request = RequestFactory()
        otheruser_request.user = self.superuser

        actual_enabled_state = self.version_admin._get_unlock_link(version, otheruser_request)

        # The url link should keep the sideframe open
        self.assertIn("js-keep-sideframe", actual_enabled_state)
        self.assertNotIn("js-close-sideframe", actual_enabled_state)
