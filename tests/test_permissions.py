from unittest.mock import patch

from django.core.checks import messages

from djangocms_versioning import constants
from djangocms_versioning.models import StateTracking, Version
from djangocms_versioning.test_utils import factories
from djangocms_versioning.test_utils.blogpost.cms_config import BlogpostCMSConfig
from djangocms_versioning.test_utils.polls.cms_config import PollsCMSConfig
from tests.test_admin import BaseStateTestCase


class PermissionTestCase(BaseStateTestCase):
    def setUp(self):
        self.versionable = BlogpostCMSConfig.versioning[0]
        self.poll_versionable = PollsCMSConfig.versioning[0]

    def get_user(self, username, is_staff=True):
        user = factories.UserFactory(username=username, is_staff=is_staff)
        user.set_password(username)
        user.save()
        return user

    @patch("django.contrib.messages.add_message")
    def test_publish_view_cannot_be_accessed_without_permission(
        self, mocked_messages
    ):
        post_version = factories.BlogPostVersionFactory(state=constants.DRAFT)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "publish", post_version.pk
        )

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertRedirectsToPreview(response, post_version)

        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], messages.ERROR)
        self.assertEqual(mocked_messages.call_args[0][2], "You do not have permission to perform this action")

        # status hasn't changed
        post_version = Version.objects.get(pk=post_version.pk)
        self.assertEqual(post_version.state, constants.DRAFT)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    @patch("django.contrib.messages.add_message")
    def test_unpublish_view_cannot_be_accessed_without_permission(
        self, mocked_messages
    ):
        post_version = factories.BlogPostVersionFactory(state=constants.PUBLISHED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "unpublish", post_version.pk
        )

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertRedirectsToPreview(response, post_version)

        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], messages.ERROR)
        self.assertEqual(mocked_messages.call_args[0][2], "You do not have permission to perform this action")

        # status hasn't changed
        post_version = Version.objects.get(pk=post_version.pk)
        self.assertEqual(post_version.state, constants.PUBLISHED)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)


    @patch("django.contrib.messages.add_message")
    def test_publish_view_can_be_accessed_with_low_level_permission(
        self, mocked_messages
    ):
        # alice has no permission to publish bob's post
        post_version = factories.BlogPostVersionFactory(state=constants.DRAFT, content__text="bob's post")
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "publish", post_version.pk
        )

        with self.login_user_context(self.get_user("bob")):
            self.client.post(url)

        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], messages.INFO)
        self.assertEqual(mocked_messages.call_args[0][2], "Version published")

        # status has changed
        post_version = Version.objects.get(pk=post_version.pk)
        self.assertEqual(post_version.state, constants.PUBLISHED)
        # status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 1)

    @patch("django.contrib.messages.add_message")
    def test_publish_view_cannot_be_accessed_wo_low_level_permission(
        self, mocked_messages
    ):
        # alice has no permission to publish bob's post
        post_version = factories.BlogPostVersionFactory(state=constants.DRAFT, content__text="bob's post")
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "publish", post_version.pk
        )

        with self.login_user_context(self.get_user("alice")):
            response = self.client.post(url)

        self.assertRedirectsToPreview(response, post_version)

        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], messages.ERROR)
        self.assertEqual(mocked_messages.call_args[0][2], "You do not have permission to perform this action")

        # status hasn't changed
        post_version = Version.objects.get(pk=post_version.pk)
        self.assertEqual(post_version.state, constants.DRAFT)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    @patch("django.contrib.messages.add_message")
    def test_unpublish_view_can_be_accessed_with_low_level_permission(
        self, mocked_messages
    ):
        # bob has permission to unpublish bob's post
        post_version = factories.BlogPostVersionFactory(state=constants.PUBLISHED, content__text="bob's post")
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "unpublish", post_version.pk
        )

        with self.login_user_context(self.get_user("bob")):
            self.client.post(url)

        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], messages.INFO)
        self.assertEqual(mocked_messages.call_args[0][2], "Version unpublished")

        # status has changed
        post_version = Version.objects.get(pk=post_version.pk)
        self.assertEqual(post_version.state, constants.UNPUBLISHED)
        # status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 1)

    @patch("django.contrib.messages.add_message")
    def test_unpublish_view_cannot_be_accessed_wo_low_level_permission(
        self, mocked_messages
    ):
        # alice has no permission to unpublish bob's post
        post_version = factories.BlogPostVersionFactory(state=constants.PUBLISHED, content__text="bob's post")
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "unpublish", post_version.pk
        )

        with self.login_user_context(self.get_user("alice")):
            response = self.client.post(url)

        self.assertRedirectsToPreview(response, post_version)

        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], messages.ERROR)
        self.assertEqual(mocked_messages.call_args[0][2], "You do not have permission to perform this action")

        # status hasn't changed
        post_version = Version.objects.get(pk=post_version.pk)
        self.assertEqual(post_version.state, constants.PUBLISHED)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    @patch("django.contrib.messages.add_message")
    def test_archive_view_cannot_be_accessed_without_permission(
        self, mocked_messages
    ):
        post_version = factories.BlogPostVersionFactory(state=constants.DRAFT)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "archive", post_version.pk
        )
        user = self.get_staff_user_with_no_permissions()

        with self.login_user_context(user):
            self.client.post(url)

        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], messages.ERROR)
        self.assertEqual(mocked_messages.call_args[0][2], "You do not have permission to perform this action")

        # status hasn't changed
        post_version = Version.objects.get(pk=post_version.pk)
        self.assertEqual(post_version.state, constants.DRAFT)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    @patch("django.contrib.messages.add_message")
    def test_archive_view_can_be_accessed_with_permission(
        self, mocked_messages
    ):
        poll_version = factories.PollVersionFactory(state=constants.DRAFT)
        url = self.get_admin_url(
            self.poll_versionable.version_model_proxy, "archive", poll_version.pk
        )
        user = self.get_staff_user_with_no_permissions()
        user.user_permissions.add(self.get_permission("change_pollcontent"))

        with self.login_user_context(user):
            self.client.post(url)

        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], messages.INFO)
        self.assertEqual(mocked_messages.call_args[0][2], "Version archived")

        # status has changed
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.ARCHIVED)
        # status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 1)

    @patch("django.contrib.messages.add_message")
    def test_revert_view_cannot_be_accessed_without_permission(
        self, mocked_messages
    ):
        post_version = factories.BlogPostVersionFactory(state=constants.ARCHIVED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "revert", post_version.pk
        )
        user = self.get_staff_user_with_no_permissions()

        with self.login_user_context(user):
            self.client.post(url)

        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], messages.ERROR)
        self.assertEqual(mocked_messages.call_args[0][2], "You do not have permission to perform this action")

        # status hasn't changed
        poll_version_ = Version.objects.get(pk=post_version.pk)
        self.assertEqual(poll_version_.state, constants.ARCHIVED)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    @patch("django.contrib.messages.add_message")
    def test_revert_view_can_be_accessed_with_low_level_permission(
        self, mocked_messages
    ):
        post_version = factories.BlogPostVersionFactory(state=constants.ARCHIVED, content__text="post <alice>")
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "revert", post_version.pk
        )
        user = self.get_user("alice", is_staff=True)
        with self.login_user_context(user):
            self.client.post(url)

        # new draft has been created
        post_version_ = Version.objects.filter(
            content_type=post_version.content_type,
            object_id__gt=post_version.object_id,
            pk__gt=post_version.pk
        ).first()
        self.assertIsNotNone(post_version_)
        self.assertEqual(post_version_.state, constants.DRAFT)
        self.assertTrue(post_version_.content.has_change_permission(user))  # Content was copied
