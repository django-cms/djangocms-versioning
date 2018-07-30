from django_fsm import TransitionNotAllowed

from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning import constants
from djangocms_versioning.models import Version
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
        version.archive()
        self.assertEqual(version.state, constants.ARCHIVED)

    def test_draft_can_change_to_published(self):
        version = factories.PollVersionFactory(state=constants.DRAFT)
        version.publish()
        self.assertEqual(version.state, constants.PUBLISHED)

    def test_draft_cant_change_to_unpublished(self):
        version = factories.PollVersionFactory(state=constants.DRAFT)
        with self.assertRaises(TransitionNotAllowed):
            version.unpublish()

    def test_archived_cant_change_to_published(self):
        version = factories.PollVersionFactory(state=constants.ARCHIVED)
        with self.assertRaises(TransitionNotAllowed):
            version.publish()

    def test_archived_cant_change_to_unpublished(self):
        version = factories.PollVersionFactory(state=constants.ARCHIVED)
        with self.assertRaises(TransitionNotAllowed):
            version.unpublish()

    def test_published_can_change_to_unpublished(self):
        version = factories.PollVersionFactory(state=constants.PUBLISHED)
        version.unpublish()
        self.assertEqual(version.state, constants.UNPUBLISHED)

    def test_published_cant_change_to_archived(self):
        version = factories.PollVersionFactory(state=constants.PUBLISHED)
        with self.assertRaises(TransitionNotAllowed):
            version.archive()

    def test_unpublished_cant_change_to_published(self):
        version = factories.PollVersionFactory(state=constants.UNPUBLISHED)
        with self.assertRaises(TransitionNotAllowed):
            version.publish()

    def test_unpublished_cant_change_to_archived(self):
        version = factories.PollVersionFactory(state=constants.UNPUBLISHED)
        with self.assertRaises(TransitionNotAllowed):
            version.archive()
