import copy

from django.apps import apps

from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.datastructures import VersionableItem, default_copy
from djangocms_versioning.models import Version
from djangocms_versioning.test_utils.factories import PollVersionFactory
from djangocms_versioning.test_utils.people.models import PersonContent
from djangocms_versioning.test_utils.polls.models import Poll, PollContent


class VersionableItemTestCase(CMSTestCase):
    def setUp(self):
        self.initial_version = PollVersionFactory()

    def test_distinct_groupers(self):
        latest_poll1_version = PollVersionFactory(
            content__poll=self.initial_version.content.poll
        )
        poll2_version = PollVersionFactory()
        PollVersionFactory(content__poll=poll2_version.content.poll)
        latest_poll2_version = PollVersionFactory(
            content__poll=poll2_version.content.poll
        )

        versionable = VersionableItem(
            content_model=PollContent,
            grouper_field_name="poll",
            copy_function=default_copy,
        )

        self.assertQuerysetEqual(
            versionable.distinct_groupers(),
            [latest_poll1_version.pk, latest_poll2_version.pk],
            transform=lambda x: x.pk,
            ordered=False,
        )

    def test_for_grouper(self):
        poll1_version2 = PollVersionFactory(
            content__poll=self.initial_version.content.poll
        )
        poll2_version = PollVersionFactory()
        PollVersionFactory(content__poll=poll2_version.content.poll)
        PollVersionFactory(content__poll=poll2_version.content.poll)

        versionable = VersionableItem(
            content_model=PollContent,
            grouper_field_name="poll",
            copy_function=default_copy,
        )

        self.assertQuerysetEqual(
            versionable.for_grouper(self.initial_version.content.poll),
            [self.initial_version.content.pk, poll1_version2.content.pk],
            transform=lambda x: x.pk,
            ordered=False,
        )

    def test_grouper_model(self):
        versionable = VersionableItem(
            content_model=PollContent,
            grouper_field_name="poll",
            copy_function=default_copy,
        )

        self.assertEqual(versionable.grouper_model, Poll)


class VersionableItemProxyModelTestCase(CMSTestCase):
    @classmethod
    def setUpClass(cls):
        cls._all_models = copy.deepcopy(apps.all_models)

    @classmethod
    def tearDownClass(cls):
        apps.all_models = cls._all_models

    def tearDown(self):
        apps.all_models.pop("djangocms_versioning", None)

    def test_version_model_proxy(self):
        versionable = VersionableItem(
            content_model=PersonContent,
            grouper_field_name="person",
            copy_function=default_copy,
        )
        version_model_proxy = versionable.version_model_proxy

        self.assertIn(Version, version_model_proxy.mro())
        self.assertEqual(version_model_proxy.__name__, "PersonContentVersion")
        self.assertEqual(version_model_proxy._source_model, PersonContent)
        self.assertTrue(version_model_proxy._meta.proxy)

    def test_version_model_proxy_cached(self):
        """Test that version_model_proxy property is cached
        and return value is created once."""
        versionable = VersionableItem(
            content_model=PersonContent,
            grouper_field_name="person",
            copy_function=default_copy,
        )

        self.assertEqual(
            id(versionable.version_model_proxy), id(versionable.version_model_proxy)
        )
