from datetime import timedelta

from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q
from django.utils import timezone

from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.models import Campaign
from djangocms_versioning.test_utils.polls.models import (
    Answer,
    Poll,
    PollContent,
    PollVersion,
    VersionWithoutGrouperField,
)


class ModelsVersioningTestCase(CMSTestCase):

    def setUp(self):
        self.initial_version = self._create_initial_poll_version('poll 1')

    def _create_initial_poll_version(self, name):
        poll = Poll.objects.create(name=name)
        poll_content = PollContent.objects.create(
            poll=poll, language='en', text='{} - Content'.format(name),
        )
        Answer.objects.create(
            poll_content=poll_content, text='{} - Answer 1'.format(name),
        )
        Answer.objects.create(
            poll_content=poll_content, text='{} - Answer 2'.format(name),
        )
        return PollVersion.objects.create(
            start=timezone.now(),
            content=poll_content,
        )

    def test_content_object_gets_duplicated(self):
        new_version = self.initial_version.copy()
        self.assertEqual(
            self.initial_version.content.text,
            new_version.content.text,
        )
        self.assertEqual(
            self.initial_version.content.language,
            new_version.content.language,
        )
        self.assertNotEqual(
            self.initial_version.content_id,
            new_version.content_id,
        )

    def test_answers_get_duplicated(self):
        new_version = self.initial_version.copy()
        self.assertEqual(
            list(self.initial_version.content.answer_set.values_list('text')),
            list(new_version.content.answer_set.values_list('text')),
        )
        self.assertNotEqual(
            list(self.initial_version.content.answer_set.values_list('pk')),
            list(new_version.content.answer_set.values_list('pk')),
        )

    def test_campaigns_duplicated(self):
        campaign_1 = Campaign.objects.create(name='Campaign 1')
        campaign_2 = Campaign.objects.create(name='Campaign 2')
        self.initial_version.campaigns.add(campaign_1, campaign_2)

        new_version = self.initial_version.copy()

        self.assertEqual(new_version.campaigns.count(), 2)
        self.assertEqual(
            list(self.initial_version.campaigns.all()),
            list(new_version.campaigns.all())
        )

    def test_distinct_groupers(self):
        self.initial_version.copy()
        poll2_version = self._create_initial_poll_version('poll 2')
        poll2_version.copy()
        poll2_version.copy()

        self.assertEqual(PollVersion.objects.distinct_groupers().count(), 2)

    def test_for_grouper(self):
        self.initial_version.copy()
        poll2_version = self._create_initial_poll_version('poll 2')
        poll2_version.copy()
        poll2_version.copy()

        qs = PollVersion.objects.for_grouper(self.initial_version.content.poll)
        self.assertEqual(qs.count(), 2)

    def test_for_grouper_extra_filters(self):
        version2 = self.initial_version.copy()
        version2.content.language = 'de'
        version2.content.save()
        poll2_version = self._create_initial_poll_version('poll 2')
        poll2_version.copy()
        poll2_version.copy()

        qs = PollVersion.objects.for_grouper(
            self.initial_version.content.poll,
            Q(content__language='en'),
        )
        self.assertEqual(qs.count(), 1)

    def test_public(self):
        now = timezone.now()

        version2 = self.initial_version.copy()
        version3 = version2.copy()
        version3.start += timedelta(days=3)
        version3.end = version3.start + timedelta(days=10)
        version3.save()
        version4 = version3.copy()
        version4.is_active = False
        version4.save()

        def _public(when=None):
            return PollVersion.objects.for_grouper(
                self.initial_version.content.poll,
                Q(content__language='en'),
            ).public(when)

        self.assertEqual(_public(), version2)
        self.assertEqual(_public(now + timedelta(days=5)), version3)
        self.assertEqual(_public(now + timedelta(days=13)), version2)

    def test_runtime_error_raised_without_grouper_field_override(self):
        version_without_grouper = VersionWithoutGrouperField()

        with self.assertRaises(ImproperlyConfigured):
            version_without_grouper.grouper_field
