from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from cms.models import Page
from cms.test_utils.testcases import CMSTestCase
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import models, transaction
from django.utils import timezone

from djangocms_versioning import conf, constants, models as versioning_models
from djangocms_versioning.models import Version
from djangocms_versioning.test_utils import factories
from djangocms_versioning.test_utils.blogpost.models import (
    BlogContent,
    BlogPost,
)
from djangocms_versioning.test_utils.polls.models import Answer, Poll, PollContent, PollPlugin


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


@patch.object(conf, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
@patch.object(versioning_models, "ALLOW_DELETING_VERSIONS", constants.DELETE_ANY)
class DeleteUnpublishedCleanupTestCase(CMSTestCase):
    def old_version(self, factory=factories.PollVersionFactory, **kwargs):
        version = factory(state=constants.UNPUBLISHED, **kwargs)
        Version.objects.filter(pk=version.pk).update(modified=timezone.now() - timedelta(days=100))
        return version

    def cleanup(self, **kwargs):
        out = StringIO()
        call_command("delete_unpublished_versions", interactive=False, stdout=out, **kwargs)
        return out.getvalue()

    def page(self, parent=None):
        site = Site.objects.get_current()
        if factories.TreeNode:
            node = parent.node.add_child(site=site) if parent else factories.TreeNode.add_root(site=site)
            return factories.PageFactory(node=node)
        return parent.add_child(site=site) if parent else Page.add_root(site=site)

    def test_content_without_override_is_deleted_in_bulk(self):
        versions = [self.old_version() for _ in range(3)]
        original_delete = models.QuerySet.delete
        content_batches = []

        def delete(queryset):
            if queryset.model is PollContent:
                content_batches.append(set(queryset.values_list("pk", flat=True)))
            return original_delete(queryset)

        with patch.object(models.QuerySet, "delete", delete):
            output = self.cleanup()

        self.assertEqual(content_batches, [{version.object_id for version in versions}])
        self.assertIn("Deleted 3 version(s).", output)

    def test_content_delete_override_runs_without_requiring_return_value(self):
        versions = [self.old_version() for _ in range(3)]
        deleted_ids = []

        def delete(content):
            deleted_ids.append(content.pk)
            models.Model.delete(content)

        with patch.object(PollContent, "delete", delete):
            output = self.cleanup(batch_size=2)

        self.assertCountEqual(deleted_ids, [version.object_id for version in versions])
        self.assertFalse(Version.objects.filter(pk__in=[version.pk for version in versions]).exists())
        self.assertIn("Deleted 3 version(s).", output)

    def test_custom_delete_that_keeps_content_is_not_counted(self):
        version = self.old_version()
        with patch.object(PollContent, "delete", return_value=None):
            output = self.cleanup()
        self.assertTrue(Version.objects.filter(pk=version.pk).exists())
        self.assertIn("Deleted 0 version(s).", output)

    def test_protected_content_does_not_block_batch_or_later_batches(self):
        versions = [self.old_version() for _ in range(5)]
        answer = factories.AnswerFactory(poll_content=versions[0].content)
        field = Answer._meta.get_field("poll_content")
        with patch.object(field.remote_field, "on_delete", models.PROTECT):
            output = self.cleanup(batch_size=2, verbosity=2)

        self.assertTrue(Version.objects.filter(pk=versions[0].pk).exists())
        self.assertTrue(PollContent._base_manager.filter(pk=versions[0].object_id).exists())
        self.assertTrue(Answer.objects.filter(pk=answer.pk).exists())
        self.assertFalse(Version.objects.filter(pk__in=[version.pk for version in versions[1:]]).exists())
        self.assertIn("Deleted 4 version(s).", output)
        self.assertIn("1 version(s) were kept", output)
        self.assertIn("polls.PollContent: 4 version(s) deleted", output)

    def test_protected_custom_delete_rolls_back_and_continues(self):
        protected = self.old_version()
        deletable = self.old_version()
        original_text = protected.content.text

        def delete(content):
            if content.pk == protected.object_id:
                PollContent._base_manager.filter(pk=content.pk).update(text="must be rolled back")
                raise models.ProtectedError("Custom cleanup is protected", [content])
            models.Model.delete(content)

        with patch.object(PollContent, "delete", delete):
            output = self.cleanup(verbosity=0)

        protected.content.refresh_from_db()
        self.assertEqual(protected.content.text, original_text)
        self.assertTrue(Version.objects.filter(pk=protected.pk).exists())
        self.assertFalse(Version.objects.filter(pk=deletable.pk).exists())
        self.assertIn("Deleted 1 version(s).", output)
        self.assertIn("1 version(s) were kept", output)

    def test_non_page_groupers_use_instance_delete(self):
        version = self.old_version()
        poll_id = version.content.poll_id
        deleted_ids = []

        def delete(poll):
            deleted_ids.append(poll.pk)
            models.Model.delete(poll)

        with patch.object(Poll, "delete", delete):
            output = self.cleanup(delete_empty_groupers=True)

        self.assertEqual(deleted_ids, [poll_id])
        self.assertFalse(Poll.objects.filter(pk=poll_id).exists())
        self.assertIn("Deleted 1 empty polls.Poll object(s).", output)

    def test_protected_grouper_does_not_block_other_groupers(self):
        protected = self.old_version()
        deletable = self.old_version()
        protected_poll = protected.content.poll
        deletable_poll = deletable.content.poll
        plugin = PollPlugin.objects.create(poll=protected_poll)
        field = PollPlugin._meta.get_field("poll")

        with patch.object(field.remote_field, "on_delete", models.PROTECT):
            output = self.cleanup(delete_empty_groupers=True)

        self.assertFalse(Version.objects.filter(pk__in=[protected.pk, deletable.pk]).exists())
        self.assertTrue(Poll.objects.filter(pk=protected_poll.pk).exists())
        self.assertTrue(PollPlugin.objects.filter(pk=plugin.pk).exists())
        self.assertFalse(Poll.objects.filter(pk=deletable_poll.pk).exists())
        self.assertIn("Cannot delete empty polls.Poll", output)
        self.assertIn("Deleted 1 empty polls.Poll object(s).", output)

    def test_all_groupers_with_remaining_content_are_kept(self):
        version = self.old_version(content__language="en")
        kept = factories.PollVersionFactory(content__poll=version.content.poll, content__language="de")
        self.cleanup(delete_empty_groupers=True)
        self.assertFalse(Version.objects.filter(pk=version.pk).exists())
        self.assertTrue(Version.objects.filter(pk=kept.pk).exists())
        self.assertTrue(Poll.objects.filter(pk=kept.content.poll_id).exists())

    def test_page_descendants_with_retained_content_are_kept(self):
        for state in (constants.PUBLISHED, constants.DRAFT, constants.UNPUBLISHED, constants.ARCHIVED):
            with self.subTest(state=state):
                parent = self.page()
                child = self.page(parent)
                old = self.old_version(factories.PageVersionFactory, content__page=parent)
                kept = factories.PageVersionFactory(content__page=child, state=state)

                output = self.cleanup(delete_empty_groupers=True)

                self.assertFalse(Version.objects.filter(pk=old.pk).exists())
                self.assertTrue(Page.objects.filter(pk=parent.pk).exists())
                self.assertTrue(Page.objects.filter(pk=child.pk).exists())
                self.assertTrue(Version.objects.filter(pk=kept.pk).exists())
                self.assertIn("it still has descendants", output)

    def test_empty_descendant_outside_candidates_is_kept(self):
        parent = self.page()
        child = self.page(parent)
        self.old_version(factories.PageVersionFactory, content__page=parent)
        self.cleanup(delete_empty_groupers=True)
        self.assertTrue(Page.objects.filter(pk=parent.pk).exists())
        self.assertTrue(Page.objects.filter(pk=child.pk).exists())

    def test_eligible_page_branch_is_deleted_deepest_first(self):
        parent = self.page()
        child = self.page(parent)
        leaf = self.page(child)
        for page in (parent, child, leaf):
            self.old_version(factories.PageVersionFactory, content__page=page)
        original_delete = Page.delete
        deleted_ids = []

        def delete(page):
            deleted_ids.append(page.pk)
            original_delete(page)

        with patch.object(Page, "delete", delete):
            output = self.cleanup(delete_empty_groupers=True, batch_size=1)

        self.assertEqual(deleted_ids, [leaf.pk, child.pk, parent.pk])
        self.assertFalse(Page.objects.filter(pk__in=deleted_ids).exists())
        self.assertIn("Deleted 3 empty cms.Page object(s).", output)

    def test_page_deletion_updates_parent_child_count(self):
        parent = self.page()
        child = self.page(parent)
        factories.PageVersionFactory(content__page=parent, state=constants.PUBLISHED)
        self.old_version(factories.PageVersionFactory, content__page=child)

        self.cleanup(delete_empty_groupers=True)

        self.assertFalse(Page.objects.filter(pk=child.pk).exists())
        node = parent.node if factories.TreeNode else parent
        node.refresh_from_db()
        self.assertEqual(node.numchild, 0)

    def test_invalid_numeric_options_do_not_delete(self):
        version = self.old_version()
        for options in ({"days": -1}, {"batch_size": 0}, {"batch_size": -1}):
            with self.subTest(options=options), self.assertRaises(CommandError):
                self.cleanup(**options)
        self.assertTrue(Version.objects.filter(pk=version.pk).exists())

    def test_created_date_can_be_used_instead_of_modified(self):
        version = factories.PollVersionFactory(state=constants.UNPUBLISHED)
        Version.objects.filter(pk=version.pk).update(created=timezone.now() - timedelta(days=100))
        self.cleanup()
        self.assertTrue(Version.objects.filter(pk=version.pk).exists())
        self.cleanup(date_field="created")
        self.assertFalse(Version.objects.filter(pk=version.pk).exists())
