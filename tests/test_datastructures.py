from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.datastructures import VersionableItem
from djangocms_versioning.test_utils.factories import PollVersionFactory
from djangocms_versioning.test_utils.polls.models import PollContent


class VersionableItemTestCase(CMSTestCase):

    def setUp(self):
        self.initial_version = PollVersionFactory()

    def test_distinct_groupers(self):
        latest_poll1_version = PollVersionFactory(
            content__poll=self.initial_version.content.poll,
        )
        poll2_version = PollVersionFactory()
        PollVersionFactory(content__poll=poll2_version.content.poll)
        latest_poll2_version = PollVersionFactory(content__poll=poll2_version.content.poll)

        versionable = VersionableItem(content_model=PollContent, grouper_field_name='poll')

        self.assertQuerysetEqual(
            versionable.distinct_groupers(),
            [latest_poll1_version.pk, latest_poll2_version.pk],
            transform=lambda x: x.pk,
            ordered=False
        )

    def test_for_grouper(self):
        poll1_version2 = PollVersionFactory(
            content__poll=self.initial_version.content.poll,
        )
        poll2_version = PollVersionFactory()
        PollVersionFactory(content__poll=poll2_version.content.poll)
        PollVersionFactory(content__poll=poll2_version.content.poll)

        versionable = VersionableItem(content_model=PollContent, grouper_field_name='poll')

        self.assertQuerysetEqual(
            versionable.for_grouper(self.initial_version.content.poll),
            [self.initial_version.content.pk, poll1_version2.content.pk],
            transform=lambda x: x.pk,
            ordered=False
        )
