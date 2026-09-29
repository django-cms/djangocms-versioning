from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from cms.test_utils.testcases import CMSTestCase
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import transaction
from django.utils import timezone

from djangocms_versioning import conf, constants, models as versioning_models
from djangocms_versioning.models import Version
from djangocms_versioning.test_utils import factories
from djangocms_versioning.test_utils.blogpost.models import (
    BlogContent,
    BlogPost,
)
from djangocms_versioning.test_utils.polls.models import Poll, PollContent


class CreateVersionsTestCase(CMSTestCase):
    def test_create_versions(self):
        content_models_by_language = {"en": 5, "de": 2, "nl": 7}

        # Arrange:
        # Create BlogPosts and Poll w/o versioned content objects
        with transaction.atomic():
            post = BlogPost(name="my multi-lingual blog post")
            post.save()
            for language, cnt in content_models_by_language.items():
                for _i in range(cnt):
                    # Use save NOT objects.create to avoid creating Version object
                    BlogContent(blogpost=post, language=language).save()
            poll = Poll()
            poll.save()
            for language, cnt in content_models_by_language.items():
                for _i in range(cnt):
                    # Use save NOT objects.create to avoid creating Version object
                    PollContent(poll=poll, language=language).save()
        # Verify that no Version objects have been created
        self.assertEqual(Version.objects.count(), 0)

        # Act:
        # Call create_versions command
        try:
            call_command("create_versions", userid=self.get_superuser().pk, state=constants.DRAFT)
        except SystemExit as e:
            status_code = str(e)
        else:
            # the "no changes" exit code is 0
            status_code = "0"
        self.assertEqual(status_code, "0")

        # Assert:
        # Blog has no additional grouping field, i.e. all except the last blog content must be archived
        blog_contents = BlogContent.admin_manager.filter(blogpost=post, language=language).order_by("-pk")
        self.assertEqual(blog_contents[0].versions.first().state, constants.DRAFT)
        for cont in blog_contents[1:]:
            self.assertEqual(cont.versions.first().state, constants.ARCHIVED)

        # Poll has additional grouping field, i.e. for each language there must be one draft (rest archived)
        for language, _cnt in content_models_by_language.items():
            poll_contents = PollContent.admin_manager.filter(poll=poll, language=language).order_by("-pk")
            self.assertEqual(poll_contents[0].versions.first().state, constants.DRAFT)
            for cont in poll_contents[1:]:
                self.assertEqual(cont.versions.first().state, constants.ARCHIVED)


class DeleteUnpublishedVersionsTestCase(CMSTestCase):
    def _version(self, state, days_ago, **kwargs):
        """Create a version in ``state`` whose ``created``/``modified`` date lies
        ``days_ago`` days in the past."""
        version = factories.PollVersionFactory(state=state, **kwargs)
        date = timezone.now() - timedelta(days=days_ago)
        Version.objects.filter(pk=version.pk).update(created=date, modified=date)
        return version

    def test_fails_if_deleting_versions_is_disabled(self):
        with patch.object(conf, "ALLOW_DELETING_VERSIONS", constants.DELETE_NONE):
            with self.assertRaises(CommandError) as context:
                call_command("delete_unpublished_versions", interactive=False)
        self.assertIn("DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS", str(context.exception))

    @patch.object(conf, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
    @patch.object(versioning_models, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
    def test_deletes_only_old_unpublished_versions(self):
        old = self._version(constants.UNPUBLISHED, 100)
        recent = self._version(constants.UNPUBLISHED, 10)
        draft = self._version(constants.DRAFT, 100)
        published = self._version(constants.PUBLISHED, 100)
        archived = self._version(constants.ARCHIVED, 100)

        call_command("delete_unpublished_versions", interactive=False, verbosity=0)

        self.assertFalse(Version.objects.filter(pk=old.pk).exists())
        self.assertFalse(PollContent.admin_manager.filter(pk=old.object_id).exists())
        for version in (recent, draft, published, archived):
            self.assertTrue(Version.objects.filter(pk=version.pk).exists())

    @patch.object(conf, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
    @patch.object(versioning_models, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
    def test_days_option(self):
        version = self._version(constants.UNPUBLISHED, 20)

        call_command("delete_unpublished_versions", days=30, interactive=False, verbosity=0)
        self.assertTrue(Version.objects.filter(pk=version.pk).exists())

        call_command("delete_unpublished_versions", days=10, interactive=False, verbosity=0)
        self.assertFalse(Version.objects.filter(pk=version.pk).exists())

    @patch.object(conf, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
    @patch.object(versioning_models, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
    def test_archived_option(self):
        archived = self._version(constants.ARCHIVED, 100)
        unpublished = self._version(constants.UNPUBLISHED, 100)

        call_command("delete_unpublished_versions", archived=True, interactive=False, verbosity=0)

        self.assertFalse(Version.objects.filter(pk=archived.pk).exists())
        self.assertFalse(Version.objects.filter(pk=unpublished.pk).exists())

    @patch.object(conf, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
    @patch.object(versioning_models, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
    def test_dry_run_does_not_delete(self):
        version = self._version(constants.UNPUBLISHED, 100)
        out = StringIO()

        call_command("delete_unpublished_versions", dry_run=True, interactive=False, stdout=out)

        self.assertTrue(Version.objects.filter(pk=version.pk).exists())
        self.assertIn("polls.PollContent: 1", out.getvalue())
        self.assertIn("Dry run", out.getvalue())

    @patch.object(conf, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
    @patch.object(versioning_models, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
    def test_model_option(self):
        poll_version = self._version(constants.UNPUBLISHED, 100)
        blog_content = factories.BlogContentWithVersionFactory(version__state=constants.UNPUBLISHED)
        blog_version = blog_content.versions.first()
        Version.objects.filter(pk=blog_version.pk).update(modified=timezone.now() - timedelta(days=100))

        call_command(
            "delete_unpublished_versions", models=["blogpost.BlogContent"], interactive=False, verbosity=0
        )

        self.assertTrue(Version.objects.filter(pk=poll_version.pk).exists())
        self.assertFalse(Version.objects.filter(pk=blog_version.pk).exists())

    @patch.object(conf, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
    @patch.object(versioning_models, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
    def test_unknown_model_option(self):
        with self.assertRaises(CommandError) as context:
            call_command("delete_unpublished_versions", models=["polls.Poll"], interactive=False)
        self.assertIn("not a versioned content model", str(context.exception))

    @patch.object(conf, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
    @patch.object(versioning_models, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
    def test_delete_empty_groupers(self):
        poll = factories.PollFactory()
        self._version(constants.UNPUBLISHED, 100, content__poll=poll, content__language="en")
        self._version(constants.UNPUBLISHED, 100, content__poll=poll, content__language="de")
        kept_poll = factories.PollFactory()
        self._version(constants.UNPUBLISHED, 100, content__poll=kept_poll, content__language="en")
        self._version(constants.DRAFT, 100, content__poll=kept_poll, content__language="de")

        call_command(
            "delete_unpublished_versions", delete_empty_groupers=True, interactive=False, verbosity=0
        )

        self.assertFalse(Poll.objects.filter(pk=poll.pk).exists())
        self.assertTrue(Poll.objects.filter(pk=kept_poll.pk).exists())

    @patch.object(conf, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
    @patch.object(versioning_models, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
    def test_groupers_are_kept_by_default(self):
        poll = factories.PollFactory()
        self._version(constants.UNPUBLISHED, 100, content__poll=poll, content__language="en")

        call_command("delete_unpublished_versions", interactive=False, verbosity=0)

        self.assertEqual(PollContent.admin_manager.filter(poll=poll).count(), 0)
        self.assertTrue(Poll.objects.filter(pk=poll.pk).exists())

    @patch.object(conf, "ALLOW_DELETING_VERSIONS", constants.DELETE_NON_PUBLIC_ONLY)
    @patch.object(versioning_models, "ALLOW_DELETING_VERSIONS", constants.DELETE_NON_PUBLIC_ONLY)
    def test_sources_of_published_versions_are_kept(self):
        """With DELETE_NON_PUBLIC_ONLY an unpublished version that a published version
        was copied from is protected and must be skipped rather than crash the command."""
        superuser = self.get_superuser()
        source = factories.PollVersionFactory(state=constants.DRAFT)
        source.publish(user=superuser)
        successor = source.copy(created_by=superuser)
        successor.publish(user=superuser)
        self.assertEqual(Version.objects.get(pk=source.pk).state, constants.UNPUBLISHED)
        Version.objects.filter(pk=source.pk).update(modified=timezone.now() - timedelta(days=100))
        out = StringIO()

        call_command("delete_unpublished_versions", interactive=False, stdout=out)

        self.assertTrue(Version.objects.filter(pk=source.pk).exists())
        # The version is filtered out up front, so it is not even reported as a candidate
        self.assertIn("No unpublished version older than 90 day(s) found.", out.getvalue())

    @patch.object(conf, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
    @patch.object(versioning_models, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
    def test_batching_deletes_everything(self):
        versions = [self._version(constants.UNPUBLISHED, 100) for _ in range(5)]

        call_command("delete_unpublished_versions", batch_size=2, interactive=False, verbosity=0)

        self.assertFalse(Version.objects.filter(pk__in=[v.pk for v in versions]).exists())

    @patch.object(conf, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
    @patch.object(versioning_models, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
    def test_nothing_to_delete(self):
        out = StringIO()

        call_command("delete_unpublished_versions", interactive=False, stdout=out)

        self.assertIn("No unpublished version older than 90 day(s) found.", out.getvalue())

    @patch.object(conf, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
    @patch.object(versioning_models, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
    @patch("builtins.input", return_value="n")
    def test_declined_confirmation_deletes_nothing(self, mocked_input):
        version = self._version(constants.UNPUBLISHED, 100)
        out = StringIO()

        call_command("delete_unpublished_versions", stdout=out)

        self.assertTrue(Version.objects.filter(pk=version.pk).exists())
        self.assertIn("Aborted", out.getvalue())

    @patch.object(conf, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
    @patch.object(versioning_models, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
    @patch("builtins.input", return_value="y")
    def test_accepted_confirmation_deletes(self, mocked_input):
        version = self._version(constants.UNPUBLISHED, 100)

        call_command("delete_unpublished_versions", verbosity=0)

        self.assertFalse(Version.objects.filter(pk=version.pk).exists())
