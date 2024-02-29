from unittest import skip

from cms.models import PlaceholderRelationField
from cms.test_utils.testcases import CMSTestCase
from cms.toolbar.items import TemplateItem
from cms.toolbar.utils import get_object_preview_url
from cms.utils import get_current_site
from django.contrib import admin
from django.contrib.auth.models import Permission
from django.core import mail
from django.template.loader import render_to_string
from django.test import RequestFactory, override_settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from djangocms_versioning import (
    admin as versioning_admin,
    conf,
    models as versioning_models,
)
from djangocms_versioning.cms_config import VersioningCMSConfig
from djangocms_versioning.constants import ARCHIVED, DRAFT, PUBLISHED, UNPUBLISHED
from djangocms_versioning.emails import get_full_url
from djangocms_versioning.helpers import (
    create_version_lock,
    placeholder_content_is_unlocked_for_user,
    version_list_url,
)
from djangocms_versioning.models import Version
from djangocms_versioning.test_utils import factories
from djangocms_versioning.test_utils.blogpost.models import BlogPost
from djangocms_versioning.test_utils.factories import (
    FancyPollFactory,
    PageVersionFactory,
    PlaceholderFactory,
    UserFactory,
)
from djangocms_versioning.test_utils.polls.cms_config import PollsCMSConfig
from djangocms_versioning.test_utils.test_helpers import (
    find_toolbar_buttons,
    get_toolbar,
    toolbar_button_exists,
)


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
        request = RequestFactory().get("/admin/djangocms_versioning/pollcontentversion/")
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
        url = self.get_admin_url(self.versionable.content_model, "change", version.content.pk)

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

        url = self.get_admin_url(self.versionable.content_model, "change", version.content.pk)
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

    def test_unlock_view_refuses_get(self):
        poll_version = factories.PollVersionFactory(
            state=PUBLISHED,
            created_by=self.superuser,
            locked_by=self.superuser,
        )
        unlock_url = self.get_admin_url(self.versionable.version_model_proxy, "unlock", poll_version.pk)

        # 404 when not in draft
        with self.login_user_context(self.superuser):
            response = self.client.get(unlock_url, follow=True)

        self.assertEqual(response.status_code, 405)

    def test_unlock_view_redirects_to_admin_dashboard_for_non_existent_id(self):
        poll_version = factories.PollVersionFactory(
            state=PUBLISHED,
            created_by=self.superuser,
            locked_by=self.superuser,
        )
        unlock_url = self.get_admin_url(self.versionable.version_model_proxy, "unlock",
                                        poll_version.pk+314159)

        # 404 when not in draft
        with self.login_user_context(self.superuser):
            response = self.client.post(unlock_url, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "dashboard")

    def test_unlock_view_redirects_404_when_not_draft(self):
        poll_version = factories.PollVersionFactory(
            state=PUBLISHED,
            created_by=self.superuser,
            locked_by=self.superuser,
        )
        unlock_url = self.get_admin_url(self.versionable.version_model_proxy, "unlock", poll_version.pk)

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
        unlock_url = self.get_admin_url(self.versionable.version_model_proxy, "unlock", poll_version.pk)

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
        unlock_url = self.get_admin_url(self.versionable.version_model_proxy, "unlock", poll_version.pk)

        with self.login_user_context(self.user_has_unlock_perms):
            response = self.client.post(unlock_url, follow=True)

        self.assertEqual(response.status_code, 200)

        # Fetch the latest state of this version
        updated_poll_version = Version.objects.get(pk=poll_version.pk)

        # The version is not locked
        self.assertFalse(hasattr(updated_poll_version, "versionlock"))

    @skip("Requires clarification if this is still a valid requirement!")
    def test_unlock_link_not_present_for_author(self):
        # FIXME: May be redundant now as this requirement was probably removed at a later date due
        #  to the fact that an author may be asked to unlock their version for someone else to use!
        author = self.get_superuser()
        poll_version = factories.PollVersionFactory(state=DRAFT, created_by=author, locked_by=author)
        changelist_url = version_list_url(poll_version.content)
        unlock_url = self.get_admin_url(self.versionable.version_model_proxy, "unlock", poll_version.pk)
        unlock_control = render_to_string(
            "djangocms_version_locking/admin/unlock_icon.html",
            {"unlock_url": unlock_url}
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
        unlock_url = self.get_admin_url(self.versionable.version_model_proxy, "unlock", poll_version.pk)

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
        unlock_url = self.get_admin_url(self.versionable.version_model_proxy, "unlock", poll_version.pk)
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
        draft_unlock_url = self.get_admin_url(self.versionable.version_model_proxy, "unlock", draft_version.pk)
        draft_unlock_control = "cms-action-unlock"
        published_unlock_url = self.get_admin_url(self.versionable.version_model_proxy, "unlock", published_version.pk)
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
                                              "unlock", draft_version.pk)

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
            "edit_redirect", updated_draft_version.pk
        )

        # The version is still owned by the author
        self.assertEqual(updated_draft_version.created_by, self.user_author)
        # The version lock does not exist
        self.assertIsNone(updated_draft_version.locked_by)

        # Visit the edit page with a user without unlock permissions
        with self.login_user_context(self.user_has_no_unlock_perms):
            self.client.post(updated_draft_edit_url)

        updated_draft_version = Version.objects.get(pk=draft_version.pk)

        # The version is still owned by the author
        self.assertEqual(updated_draft_version.created_by, self.user_author)
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


@override_settings(DJANGOCMS_VERSIONING_LOCK_VERSIONS=True)
class VersionLockIndicatorTestCase(CMSTestCase):

    def setUp(self) -> None:
        self.LOCK_VERSIONS = conf.LOCK_VERSIONS
        conf.LOCK_VERSIONS = True

        self.superuser = self.get_superuser()
        self.user_author = self._create_user("author", is_staff=True, is_superuser=False)
        self.version_admin = admin.site._registry[BlogPost]

    def tearDown(self) -> None:
        conf.LOCK_VERSIONS = self.LOCK_VERSIONS

    def test_unlock_action_in_indicator_menu(self):
        """The indicator drop down menu contains an entry to unlock a draft."""
        changelist_url = reverse("admin:blogpost_blogpost_changelist")
        version = factories.BlogPostVersionFactory(created_by=self.user_author, locked_by=self.user_author)
        expected_unlock_url = reverse("admin:djangocms_versioning_blogcontentversion_unlock", args=(version.pk,))

        with self.login_user_context(self.superuser):
            response = self.client.get(changelist_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cms-icon cms-icon-unlock")
        self.assertContains(response, expected_unlock_url)


@override_settings(DJANGOCMS_VERSIONING_LOCK_VERSIONS=True)
class CheckLockTestCase(CMSTestCase):

    def setUp(self):
        import importlib
        importlib.reload(conf)
        importlib.reload(versioning_admin)

    def test_check_no_lock(self):
        user = self.get_superuser()
        version = PageVersionFactory(state=ARCHIVED)
        placeholder = PlaceholderFactory(source=version.content)

        self.assertTrue(placeholder_content_is_unlocked_for_user(placeholder, user))

    def test_check_locked_for_the_same_user(self):
        user = self.get_superuser()
        version = PageVersionFactory(created_by=user, locked_by=user)
        placeholder = PlaceholderFactory(source=version.content)

        self.assertTrue(placeholder_content_is_unlocked_for_user(placeholder, user))

    def test_check_locked_for_the_other_user(self):
        user1 = self.get_superuser()
        user2 = self.get_standard_user()
        version = PageVersionFactory(created_by=user1, locked_by=user1)
        placeholder = PlaceholderFactory(source=version.content)

        self.assertFalse(placeholder_content_is_unlocked_for_user(placeholder, user2))

    def test_check_no_lock_for_unversioned_model(self):
        user2 = self.get_standard_user()
        placeholder = PlaceholderFactory(source=FancyPollFactory())

        self.assertTrue(placeholder_content_is_unlocked_for_user(placeholder, user2))


@override_settings(DJANGOCMS_VERSIONING_LOCK_VERSIONS=True)
class CheckInjectTestCase(CMSTestCase):

    def setUp(self):
        import importlib
        importlib.reload(conf)
        importlib.reload(versioning_admin)

    @skip("This test would require reloading of the django app configs.")
    def test_lock_check_is_injected_into_default_checks(self):
        self.assertIn(
            placeholder_content_is_unlocked_for_user,
            PlaceholderRelationField.default_checks,
        )


@override_settings(DJANGOCMS_VERSIONING_LOCK_VERSIONS=True)
class VersionLockNotificationEmailsTestCase(CMSTestCase):

    def setUp(self):
        import importlib
        importlib.reload(conf)
        importlib.reload(versioning_admin)

        self.superuser = self.get_superuser()
        self.user_author = self._create_user("author", is_staff=True, is_superuser=False)
        self.user_has_no_perms = self._create_user("user_has_no_perms", is_staff=True, is_superuser=False)
        self.user_has_unlock_perms = self._create_user("user_has_unlock_perms", is_staff=True, is_superuser=False)
        self.versionable = VersioningCMSConfig.versioning[0]

        # Set permissions
        delete_permission = Permission.objects.get(codename="delete_versionlock")
        self.user_has_unlock_perms.user_permissions.add(delete_permission)

    def test_notify_version_author_version_unlocked_email_sent_for_different_user(self):
        """
        The user unlocking a version that is authored buy a different user
        should be sent a notification email
        """
        draft_version = factories.PageVersionFactory(content__template="", created_by=self.user_author)
        draft_unlock_url = self.get_admin_url(self.versionable.version_model_proxy,
                                              "unlock", draft_version.pk)

        # Check that no emails exist
        self.assertEqual(len(mail.outbox), 0)

        # Unlock the version with a different user with unlock permissions
        with self.login_user_context(self.user_has_unlock_perms):
            self.client.post(draft_unlock_url, follow=True)

        site = get_current_site()
        expected_subject = "[Django CMS] ({site_name}) {title} - {description}".format(
            site_name=site.name,
            title=draft_version.content,
            description=_("Unlocked"),
        )
        expected_body = f"The following draft version has been unlocked by {self.user_has_unlock_perms} for their use."
        expected_version_url = get_full_url(
            get_object_preview_url(draft_version.content)
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, expected_subject)
        self.assertEqual(mail.outbox[0].to[0], self.user_author.email)
        self.assertIn(expected_body, mail.outbox[0].body)
        self.assertIn(expected_version_url, mail.outbox[0].body)

    def test_notify_version_author_version_unlocked_email_not_sent_for_different_user(self):
        """
        The user unlocking a version that authored the version should not be
        sent a notification email
        """
        draft_version = factories.PageVersionFactory(content__template="", created_by=self.user_author)
        draft_unlock_url = self.get_admin_url(self.versionable.version_model_proxy,
                                              "unlock", draft_version.pk)

        # Check that no emails exist
        self.assertEqual(len(mail.outbox), 0)

        # Unlock the version the same user who authored it
        with self.login_user_context(self.user_author):
            self.client.post(draft_unlock_url, follow=True)

        # Check that no emails still exist
        self.assertEqual(len(mail.outbox), 0)

    def test_notify_version_author_version_unlocked_email_contents_users_full_name_used(self):
        """
        The email contains the full name of the author
        """
        user = self.user_has_unlock_perms
        user.first_name = "Firstname"
        user.last_name = "Lastname"
        user.save()
        draft_version = factories.PageVersionFactory(content__template="", created_by=self.user_author)
        draft_unlock_url = self.get_admin_url(self.versionable.version_model_proxy,
                                              "unlock", draft_version.pk)

        # Check that no emails exist
        self.assertEqual(len(mail.outbox), 0)

        # Unlock the version with a different user with unlock permissions
        with self.login_user_context(user):
            self.client.post(draft_unlock_url, follow=True)

        expected_body = f"The following draft version has been unlocked by {user.get_full_name()} for their use."

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(expected_body, mail.outbox[0].body)

    def test_notify_version_author_version_unlocked_email_contents_users_username_used(self):
        """
        The email contains the  username of the author because no name is available
        """
        user = self.user_has_unlock_perms
        draft_version = factories.PageVersionFactory(content__template="", created_by=self.user_author)
        draft_unlock_url = self.get_admin_url(self.versionable.version_model_proxy,
                                              "unlock", draft_version.pk)

        # Check that no emails exist
        self.assertEqual(len(mail.outbox), 0)

        # Unlock the version with a different user with unlock permissions
        with self.login_user_context(user):
            self.client.post(draft_unlock_url, follow=True)

        expected_body = f"The following draft version has been unlocked by {user.username} for their use."

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(expected_body, mail.outbox[0].body)


@override_settings(DJANGOCMS_VERSIONING_LOCK_VERSIONS=True)
class TestVersionsLockTestCase(CMSTestCase):

    def setUp(self):
        import importlib
        importlib.reload(conf)
        importlib.reload(versioning_admin)
        self.versionable = PollsCMSConfig.versioning[0]
        self.user = self.get_standard_user()

    def test_version_is_locked_for_draft(self):
        """
        A version lock is present when a content version is created in a draft state with a locked_by user
        """
        draft_version = factories.PollVersionFactory(state=DRAFT, created_by=self.user, locked_by=self.user)

        self.assertIsNotNone(draft_version.locked_by)

    def test_version_is_unlocked_for_publishing(self):
        """
        A version lock is not present when a content version is in a published or unpublished state
        """
        user = self.get_superuser()
        poll_version = factories.PollVersionFactory(state=DRAFT, created_by=user, locked_by=user)
        publish_url = self.get_admin_url(self.versionable.version_model_proxy, "publish", poll_version.pk)
        unpublish_url = self.get_admin_url(self.versionable.version_model_proxy, "unpublish", poll_version.pk)

        with self.login_user_context(user):
            self.client.post(publish_url)

        updated_poll_version = Version.objects.get(pk=poll_version.pk)

        # The state is now PUBLISHED
        self.assertEqual(updated_poll_version.state, PUBLISHED)
        # Version lock does not exist
        self.assertIsNone(updated_poll_version.locked_by)

        with self.login_user_context(user):
            self.client.post(unpublish_url)

        updated_poll_version = Version.objects.get(pk=poll_version.pk)

        # The state is now UNPUBLISHED
        self.assertEqual(updated_poll_version.state, UNPUBLISHED)
        # Version lock does not exist
        self.assertFalse(hasattr(updated_poll_version, "versionlock"))

    def test_version_is_unlocked_for_archived(self):
        """
        A version lock is not present when a content version is in an archived state
        """
        user = self.get_superuser()
        poll_version = factories.PollVersionFactory(state=DRAFT, created_by=user, locked_by=user)
        archive_url = self.get_admin_url(self.versionable.version_model_proxy, "archive", poll_version.pk)

        with self.login_user_context(user):
            self.client.post(archive_url)

        updated_poll_version = Version.objects.get(pk=poll_version.pk)

        # The state is now ARCHIVED
        self.assertEqual(updated_poll_version.state, ARCHIVED)
        # Version lock does not exist
        self.assertFalse(hasattr(updated_poll_version, "versionlock"))


@override_settings(DJANGOCMS_VERSIONING_LOCK_VERSIONS=True)
class TestVersionCopyLocks(CMSTestCase):

    def setUp(self) -> None:
        self.LOCK_VERSIONS = versioning_models.LOCK_VERSIONS
        versioning_models.LOCK_VERSIONS = True

    def tearDown(self) -> None:
        versioning_models.LOCK_VERSIONS = self.LOCK_VERSIONS

    def test_draft_version_copy_creates_draft_lock(self):
        """
        A version lock is created for a new draft version copied from a draft version
        """
        user = factories.UserFactory()
        draft_version = factories.PollVersionFactory(state=DRAFT)
        new_version = draft_version.copy(user)

        self.assertIsNotNone(new_version.locked_by)

    def test_published_version_copy_creates_draft_lock(self):
        """
        A version lock is created for a published version copied from a draft version
        """
        user = factories.UserFactory()
        published_version = factories.PollVersionFactory(state=PUBLISHED, locked_by=None)
        new_version = published_version.copy(user)

        self.assertIsNotNone(new_version.locked_by)

    def test_version_copy_adds_correct_locked_user(self):
        """
        A copied version creates a lock for the user that copied the version.
        The users should not be the same.
        """
        original_user = factories.UserFactory()
        original_version = factories.PollVersionFactory(created_by=original_user, locked_by=original_user)
        copy_user = factories.UserFactory()
        copied_version = original_version.copy(copy_user)

        self.assertNotEqual(original_user, copy_user)
        self.assertEqual(original_version.locked_by, original_user)
        self.assertEqual(copied_version.locked_by, copy_user)


@override_settings(DJANGOCMS_VERSIONING_LOCK_VERSIONS=True)
class VersionToolbarOverrideTestCase(CMSTestCase):

    def setUp(self) -> None:
        from cms.models.permissionmodels import GlobalPagePermission

        from djangocms_versioning import cms_toolbars
        self.LOCK_VERSIONS = cms_toolbars.LOCK_VERSIONS
        cms_toolbars.LOCK_VERSIONS = True

        self.user_has_change_perms = self._create_user(
            "user_default_perms",
            is_staff=True,
            permissions=["change_page", "add_page", "delete_page"],
        )
        # Grant permission (or Unlock button will not be shown)
        GlobalPagePermission.objects.create(
            user=self.user_has_change_perms,
        )

    def tearDown(self) -> None:
        from djangocms_versioning import cms_toolbars
        cms_toolbars.LOCK_VERSIONS = self.LOCK_VERSIONS

    def test_not_render_edit_button_when_not_content_mode(self):
        user = self.get_superuser()
        version = PageVersionFactory(created_by=user)

        toolbar = get_toolbar(version.content, user, edit_mode=True)
        toolbar.post_template_populate()

        self.assertFalse(toolbar_button_exists("Edit", toolbar.toolbar))

    def test_no_edit_button_when_content_is_locked(self):
        user = self.get_superuser()
        user_2 = UserFactory(
            is_staff=True,
            is_superuser=True,
            username="admin2",
            email="admin2@123.com",
        )
        version = PageVersionFactory(created_by=user, locked_by=user)

        toolbar = get_toolbar(version.content, user_2, content_mode=True)
        toolbar.post_template_populate()
        edit_buttons = find_toolbar_buttons("Edit", toolbar.toolbar)
        self.assertListEqual(edit_buttons, [])

    def test_disabled_unlock_button_when_content_is_locked(self):
        user = self.get_superuser()
        user_2 = self.user_has_change_perms
        version = PageVersionFactory(created_by=user, locked_by=user)

        toolbar = get_toolbar(version.content, user_2, content_mode=True)
        toolbar.post_template_populate()

        unlock_buttons = find_toolbar_buttons("Unlock", toolbar.toolbar)
        self.assertEqual(len(unlock_buttons), 1)
        self.assertEqual(unlock_buttons[0].url, "#")  # disabled

    def test_enabled_unlock_button_when_content_is_locked(self):
        user = UserFactory(
            is_staff=True,
            is_superuser=True,
            username="admin2",
            email="admin2@123.com",
        )
        version = PageVersionFactory(created_by=user, locked_by=user)
        toolbar = get_toolbar(version.content, user=self.get_superuser(), content_mode=True)
        proxy_model = toolbar._get_proxy_model()
        expected_unlock_url = reverse(
            f"admin:{proxy_model._meta.app_label}_{proxy_model.__name__.lower()}_unlock",
            args=(version.pk,),
        )
        toolbar.post_template_populate()
        unlock_buttons = find_toolbar_buttons("Unlock", toolbar.toolbar)
        self.assertEqual(unlock_buttons[0].url, expected_unlock_url)  # enabled

    def test_enable_edit_button_when_content_is_locked(self):
        from cms.models import Page
        from django.apps import apps

        user = self.get_superuser()
        version = PageVersionFactory(created_by=user)

        toolbar = get_toolbar(version.content, user, content_mode=True)
        toolbar.post_template_populate()
        edit_button = find_toolbar_buttons("Edit", toolbar.toolbar)[0]

        self.assertEqual(edit_button.name, "Edit")

        cms_extension = apps.get_app_config("djangocms_versioning").cms_extension
        versionable = cms_extension.versionables_by_grouper[Page]
        admin_url = self.get_admin_url(
            versionable.version_model_proxy, "edit_redirect", version.pk
        )
        self.assertEqual(edit_button.url, admin_url)
        self.assertFalse(edit_button.disabled)
        self.assertListEqual(
            edit_button.extra_classes,
            ["cms-btn-action", "js-action", "cms-form-post-method", "cms-versioning-js-edit-btn"]
        )

    def test_lock_message_when_content_is_locked(self):
        user = self.get_superuser()
        user.first_name = "Firstname"
        user.last_name = "Lastname"
        user.save()
        user_2 = UserFactory(
            is_staff=True,
            is_superuser=True,
            username="admin2",
            email="admin2@123.com",
        )
        version = PageVersionFactory(created_by=user, locked_by=user)

        toolbar = get_toolbar(version.content, user_2, content_mode=True)
        toolbar.post_template_populate()

        for item in toolbar.toolbar.get_right_items():
            if isinstance(item, TemplateItem) and item.template == "djangocms_versioning/admin/lock_indicator.html":
                self.assertEqual(version.locked_message(), f"Locked by {user}")
                break
        else:
            self.assertFalse("locking message not found")

    def test_edit_button_when_content_is_locked_users_username_used(self):
        user = self.get_superuser()
        user.first_name = ""
        user.last_name = ""
        user.save()
        user_2 = UserFactory(
            is_staff=True,
            is_superuser=True,
            username="admin2",
            email="admin2@123.com",
        )
        version = PageVersionFactory(created_by=user, locked_by=user)

        toolbar = get_toolbar(version.content, user_2, content_mode=True)
        toolbar.post_template_populate()
        btn_name = "Unlock"
        unlock_buttons = find_toolbar_buttons(btn_name, toolbar.toolbar)

        self.assertEqual(len(unlock_buttons), 1)


class IntegrationTestCase(CMSTestCase):

    def setUp(self) -> None:
        self.user = self.get_superuser()
        self.version = factories.PollVersionFactory(created_by=self.user, locked_by=self.user)
        self.versionable = PollsCMSConfig.versioning[0]

    def test_unlock_view_with_locking_disabled(self):
        """Tests that unlock view returns 404 if locking is disabled"""
        unlock_url = self.get_admin_url(self.versionable.version_model_proxy, "unlock", self.version.pk)

        with self.login_user_context(self.user):
            conf.LOCK_VERSIONS = False
            response = self.client.post(unlock_url)

        self.assertEqual(response.status_code, 404)
