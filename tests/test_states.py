from django.utils.timezone import now

from cms.test_utils.testcases import CMSTestCase

from django_fsm import TransitionNotAllowed
from freezegun import freeze_time

from djangocms_versioning import constants
from djangocms_versioning.models import StateTracking, Version
from djangocms_versioning.test_utils import factories


class TestVersionState(CMSTestCase):

    def test_direct_modification_of_state_not_allowed(self):
        version = factories.PollVersionFactory(state=constants.DRAFT)
        with self.assertRaises(AttributeError):
            version.state = constants.PUBLISHED
            version.save()

    def test_new_version_is_draft_by_default(self):
        # Not using PollVersionFactory for this as PollVersionFactory
        # could potentially be overriding the value of state and we
        # want to know the default
        version = Version.objects.create(
            content=factories.PollContentFactory(),
            created_by=factories.UserFactory())
        self.assertEqual(version.state, constants.DRAFT)

    def test_new_draft_causes_old_drafts_to_change_to_archived(self):
        """When versions relating to the same grouper have a new draft
        created, all old drafts should be marked archived
        """
        poll = factories.PollFactory()
        factories.PollVersionFactory.create_batch(
            3, state=constants.DRAFT, content__poll=poll)

        version = Version.objects.create(
            content=factories.PollContentFactory(poll=poll),
            created_by=factories.UserFactory(),
            state=constants.DRAFT)

        # Only one draft
        self.assertEqual(
            Version.objects.filter(state=constants.DRAFT).count(), 1)
        # Everything other than the last draft we created has status archived
        self.assertEqual(
            Version.objects.exclude(pk=version.pk).filter(state=constants.ARCHIVED).count(),
            3)

    def test_new_draft_doesnt_change_status_of_drafts_from_other_groupers(self):
        """When versions relating to different groupers have a new draft
        created, then this should not change the other draft's status to
        archived.
        """
        other_version = factories.PollVersionFactory(state=constants.DRAFT)

        version = Version.objects.create(
            content=factories.PollContentFactory(), state=constants.DRAFT,
            created_by=factories.UserFactory())

        # Both are still drafts because they relate to different groupers
        self.assertEqual(
            Version.objects.filter(state=constants.DRAFT).count(), 2)

    def test_new_draft_doesnt_change_status_of_drafts_with_other_states(self):
        """When versions relating to the same grouper have non-draft
        states, these should not change upon creating a new draft
        """
        poll = factories.PollFactory()
        factories.PollVersionFactory(state=constants.UNPUBLISHED, content__poll=poll)
        factories.PollVersionFactory(state=constants.PUBLISHED, content__poll=poll)

        version = Version.objects.create(
            content=factories.PollContentFactory(poll=poll),
            created_by=factories.UserFactory(),
            state=constants.DRAFT)

        # Nothing has an archived state cause there were no drafts
        self.assertEqual(
            Version.objects.exclude(pk=version.pk).filter(state=constants.ARCHIVED).count(),
            0)

    def test_draft_can_change_to_archived(self):
        version = factories.PollVersionFactory(state=constants.DRAFT)
        user = factories.UserFactory()
        version.archive(user)
        self.assertEqual(version.state, constants.ARCHIVED)

    def test_draft_can_change_to_published(self):
        version = factories.PollVersionFactory(state=constants.DRAFT)
        user = factories.UserFactory()
        version.publish(user)
        self.assertEqual(version.state, constants.PUBLISHED)

    def test_draft_cant_change_to_unpublished(self):
        version = factories.PollVersionFactory(state=constants.DRAFT)
        user = factories.UserFactory()
        with self.assertRaises(TransitionNotAllowed):
            version.unpublish(user)

    def test_archived_cant_change_to_published(self):
        version = factories.PollVersionFactory(state=constants.ARCHIVED)
        user = factories.UserFactory()
        with self.assertRaises(TransitionNotAllowed):
            version.publish(user)

    def test_archived_cant_change_to_unpublished(self):
        version = factories.PollVersionFactory(state=constants.ARCHIVED)
        user = factories.UserFactory()
        with self.assertRaises(TransitionNotAllowed):
            version.unpublish(user)

    def test_archived_cant_change_to_archived(self):
        version = factories.PollVersionFactory(state=constants.ARCHIVED)
        user = factories.UserFactory()
        with self.assertRaises(TransitionNotAllowed):
            version.archive(user)

    def test_published_can_change_to_unpublished(self):
        version = factories.PollVersionFactory(state=constants.PUBLISHED)
        user = factories.UserFactory()
        version.unpublish(user)
        self.assertEqual(version.state, constants.UNPUBLISHED)

    def test_published_cant_change_to_archived(self):
        version = factories.PollVersionFactory(state=constants.PUBLISHED)
        user = factories.UserFactory()
        with self.assertRaises(TransitionNotAllowed):
            version.archive(user)

    def test_published_cant_change_to_published(self):
        version = factories.PollVersionFactory(state=constants.PUBLISHED)
        user = factories.UserFactory()
        with self.assertRaises(TransitionNotAllowed):
            version.publish(user)

    def test_unpublished_cant_change_to_published(self):
        version = factories.PollVersionFactory(state=constants.UNPUBLISHED)
        user = factories.UserFactory()
        with self.assertRaises(TransitionNotAllowed):
            version.publish(user)

    def test_unpublished_cant_change_to_archived(self):
        version = factories.PollVersionFactory(state=constants.UNPUBLISHED)
        user = factories.UserFactory()
        with self.assertRaises(TransitionNotAllowed):
            version.archive(user)

    def test_unpublished_cant_change_to_unpublished(self):
        version = factories.PollVersionFactory(state=constants.UNPUBLISHED)
        user = factories.UserFactory()
        with self.assertRaises(TransitionNotAllowed):
            version.unpublish(user)


class TestVersionStateLogging(CMSTestCase):

    @freeze_time(None)
    def test_draft_change_to_archived_is_logged(self):
        version = factories.PollVersionFactory(state=constants.DRAFT)
        user = factories.UserFactory()

        version.archive(user)

        tracking = StateTracking.objects.get()
        self.assertEqual(tracking.version, version)
        self.assertEqual(tracking.date, now())
        self.assertEqual(tracking.old_state, constants.DRAFT)
        self.assertEqual(tracking.new_state, constants.ARCHIVED)
        self.assertEqual(tracking.user, user)

    @freeze_time(None)
    def test_draft_change_to_published_is_logged(self):
        version = factories.PollVersionFactory(state=constants.DRAFT)
        user = factories.UserFactory()

        version.publish(user)

        tracking = StateTracking.objects.get()
        self.assertEqual(tracking.version, version)
        self.assertEqual(tracking.date, now())
        self.assertEqual(tracking.old_state, constants.DRAFT)
        self.assertEqual(tracking.new_state, constants.PUBLISHED)
        self.assertEqual(tracking.user, user)

    @freeze_time(None)
    def test_published_change_to_unpublished_is_logged(self):
        version = factories.PollVersionFactory(state=constants.PUBLISHED)
        user = factories.UserFactory()

        version.unpublish(user)

        tracking = StateTracking.objects.get()
        self.assertEqual(tracking.version, version)
        self.assertEqual(tracking.date, now())
        self.assertEqual(tracking.old_state, constants.PUBLISHED)
        self.assertEqual(tracking.new_state, constants.UNPUBLISHED)
        self.assertEqual(tracking.user, user)
