from django_fsm import TransitionNotAllowed

from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.models import BaseVersion
from djangocms_versioning.test_utils import factories
from djangocms_versioning.test_utils.polls.models import PollVersion


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
        version = PollVersion.objects.create(
            content=factories.PollContentFactory())
        self.assertEqual(version.state, 'Draft')

    def test_draft_can_change_to_archived(self):
        version = factories.PollVersionFactory(state='Draft')
        version.archive()
        self.assertEqual(version.state, 'Archived')

    def test_draft_can_change_to_published(self):
        version = factories.PollVersionFactory(state='Draft')
        version.publish()
        self.assertEqual(version.state, 'Published')

    def test_draft_cant_change_to_unpublished(self):
        version = factories.PollVersionFactory(state='Draft')
        with self.assertRaises(TransitionNotAllowed):
            version.unpublish()

    def test_archived_cant_change_to_published(self):
        version = factories.PollVersionFactory(state='Archived')
        with self.assertRaises(TransitionNotAllowed):
            version.publish()

    def test_archived_cant_change_to_unpublished(self):
        version = factories.PollVersionFactory(state='Archived')
        with self.assertRaises(TransitionNotAllowed):
            version.unpublish()

    def test_published_can_change_to_unpublished(self):
        version = factories.PollVersionFactory(state='Published')
        version.unpublish()
        self.assertEqual(version.state, 'Unpublished')

    def test_published_cant_change_to_archived(self):
        version = factories.PollVersionFactory(state='Published')
        with self.assertRaises(TransitionNotAllowed):
            version.archive()

    def test_unpublished_cant_change_to_published(self):
        version = factories.PollVersionFactory(state='Unpublished')
        with self.assertRaises(TransitionNotAllowed):
            version.publish()

    def test_unpublished_cant_change_to_archived(self):
        version = factories.PollVersionFactory(state='Unpublished')
        with self.assertRaises(TransitionNotAllowed):
            version.archive()
