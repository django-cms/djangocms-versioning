from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.datastructures import VersionableItem
from djangocms_versioning.test_utils.factories import PollVersionFactory
from djangocms_versioning.test_utils.polls.models import PollContent


class VersionableItemTestCase(CMSTestCase):

    def setUp(self):
        self.initial_version = PollVersionFactory()

    def test_distinct_groupers(self):
        PollVersionFactory(content__poll=self.initial_version.content.poll)
        poll2_version = PollVersionFactory()
        PollVersionFactory(content__poll=poll2_version.content.poll)
        PollVersionFactory(content__poll=poll2_version.content.poll)

        versionable = VersionableItem(content_model=PollContent, grouper_field_name='poll')

        self.assertEqual(versionable.distinct_groupers().count(), 2)

    def test_for_grouper(self):
        PollVersionFactory(content__poll=self.initial_version.content.poll)
        poll2_version = PollVersionFactory()
        PollVersionFactory(content__poll=poll2_version.content.poll)
        PollVersionFactory(content__poll=poll2_version.content.poll)

        versionable = VersionableItem(content_model=PollContent, grouper_field_name='poll')

        qs = versionable.for_grouper(self.initial_version.content.poll)
        self.assertEqual(qs.count(), 2)
