from django.db.models import Q

from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.datastructures import VersionableItem
from djangocms_versioning.models import Version
from djangocms_versioning.test_utils.factories import (
    AnswerFactory,
    PollVersionFactory,
)
from djangocms_versioning.test_utils.polls.models import PollContent


class VersionableItemTestCase(CMSTestCase):

    def setUp(self):
        self.initial_version = PollVersionFactory()
        AnswerFactory.create_batch(
            2, poll_content=self.initial_version.content)

    def test_distinct_groupers(self):
        self.initial_version.copy()
        poll2_version = PollVersionFactory()
        poll2_version.copy()
        poll2_version.copy()

        versionable = VersionableItem(content_model=PollContent, grouper_field_name='poll')

        self.assertEqual(versionable.distinct_groupers().count(), 2)

    def test_for_grouper(self):
        self.initial_version.copy()
        poll2_version = PollVersionFactory()
        poll2_version.copy()
        poll2_version.copy()

        versionable = VersionableItem(content_model=PollContent, grouper_field_name='poll')

        qs = versionable.for_grouper(self.initial_version.content.poll)
        self.assertEqual(qs.count(), 2)

    def test_for_grouper_extra_filters(self):
        version2 = self.initial_version.copy()
        version2.content.language = 'de'
        version2.content.save()
        poll2_version = PollVersionFactory()
        poll2_version.copy()
        poll2_version.copy()

        versionable = VersionableItem(content_model=PollContent, grouper_field_name='poll')

        qs = versionable.for_grouper(
            self.initial_version.content.poll,
            Q(language='en'),
        )
        self.assertEqual(qs.count(), 1)
