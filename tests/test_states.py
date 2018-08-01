from freezegun import freeze_time

from django_fsm import TransitionNotAllowed
from django.utils.timezone import now

from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning import constants
from djangocms_versioning.models import Version, StateTracking
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
            content=factories.PollContentFactory())
        self.assertEqual(version.state, constants.DRAFT)

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
