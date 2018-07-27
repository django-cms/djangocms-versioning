from freezegun import freeze_time

from django_fsm import TransitionNotAllowed
from django.utils.timezone import now

from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.test_utils import factories
from djangocms_versioning.models import Version, StateTracking


class TestVersionState(CMSTestCase):

    def test_direct_modification_of_state_not_allowed(self):
        version = factories.PollVersionFactory(state='Draft')
        with self.assertRaises(AttributeError):
            version.state = 'Published'
            version.save()

    def test_new_version_is_draft_by_default(self):
        # Not using PollVersionFactory for this as PollVersionFactory
        # could potentially be overriding the value of state and we
        # want to know the default
        version = Version.objects.create(
            content=factories.PollContentFactory())
        self.assertEqual(version.state, 'Draft')

    def test_draft_can_change_to_archived(self):
        version = factories.PollVersionFactory(state='Draft')
        user = factories.UserFactory()
        version.archive(user)
        self.assertEqual(version.state, 'Archived')

    def test_draft_can_change_to_published(self):
        version = factories.PollVersionFactory(state='Draft')
        user = factories.UserFactory()
        version.publish(user)
        self.assertEqual(version.state, 'Published')

    def test_draft_cant_change_to_unpublished(self):
        version = factories.PollVersionFactory(state='Draft')
        user = factories.UserFactory()
        with self.assertRaises(TransitionNotAllowed):
            version.unpublish(user)

    def test_archived_cant_change_to_published(self):
        version = factories.PollVersionFactory(state='Archived')
        user = factories.UserFactory()
        with self.assertRaises(TransitionNotAllowed):
            version.publish(user)

    def test_archived_cant_change_to_unpublished(self):
        version = factories.PollVersionFactory(state='Archived')
        user = factories.UserFactory()
        with self.assertRaises(TransitionNotAllowed):
            version.unpublish(user)

    def test_published_can_change_to_unpublished(self):
        version = factories.PollVersionFactory(state='Published')
        user = factories.UserFactory()
        version.unpublish(user)
        self.assertEqual(version.state, 'Unpublished')

    def test_published_cant_change_to_archived(self):
        version = factories.PollVersionFactory(state='Published')
        user = factories.UserFactory()
        with self.assertRaises(TransitionNotAllowed):
            version.archive(user)

    def test_unpublished_cant_change_to_published(self):
        version = factories.PollVersionFactory(state='Unpublished')
        user = factories.UserFactory()
        with self.assertRaises(TransitionNotAllowed):
            version.publish(user)

    def test_unpublished_cant_change_to_archived(self):
        version = factories.PollVersionFactory(state='Unpublished')
        user = factories.UserFactory()
        with self.assertRaises(TransitionNotAllowed):
            version.archive(user)


class TestVersionStateLogging(CMSTestCase):

    @freeze_time(None)
    def test_draft_change_to_archived_is_logged(self):
        version = factories.PollVersionFactory(state='Draft')
        user = factories.UserFactory()

        version.archive(user)

        tracking = StateTracking.objects.get()
        self.assertEqual(tracking.version, version)
        self.assertEqual(tracking.date, now())
        self.assertEqual(tracking.old_state, 'Draft')
        self.assertEqual(tracking.new_state, 'Archived')
        self.assertEqual(tracking.user, user)

    @freeze_time(None)
    def test_draft_change_to_published_is_logged(self):
        version = factories.PollVersionFactory(state='Draft')
        user = factories.UserFactory()

        version.publish(user)

        tracking = StateTracking.objects.get()
        self.assertEqual(tracking.version, version)
        self.assertEqual(tracking.date, now())
        self.assertEqual(tracking.old_state, 'Draft')
        self.assertEqual(tracking.new_state, 'Published')
        self.assertEqual(tracking.user, user)

    @freeze_time(None)
    def test_published_change_to_unpublished_is_logged(self):
        version = factories.PollVersionFactory(state='Published')
        user = factories.UserFactory()

        version.unpublish(user)

        tracking = StateTracking.objects.get()
        self.assertEqual(tracking.version, version)
        self.assertEqual(tracking.date, now())
        self.assertEqual(tracking.old_state, 'Published')
        self.assertEqual(tracking.new_state, 'Unpublished')
        self.assertEqual(tracking.user, user)
