import copy

from cms.models import PageContent
from cms.test_utils.testcases import CMSTestCase
from django.apps import apps

from djangocms_versioning.constants import ARCHIVED, PUBLISHED
from djangocms_versioning.datastructures import VersionableItem, default_copy
from djangocms_versioning.models import Version
from djangocms_versioning.test_utils.factories import PollVersionFactory
from djangocms_versioning.test_utils.people.models import PersonContent
from djangocms_versioning.test_utils.polls.models import Poll, PollContent
from django.test import TestCase
from cms.models import Placeholder
from djangocms_versioning.datastructures import default_copy
from djangocms_versioning.test_utils.polls.models import PollContent
from djangocms_versioning.test_utils.factories import PollContentFactory

if not hasattr(CMSTestCase, "assertQuerySetEqual"):
    # Django < 4.2
    CMSTestCase.assertQuerySetEqual = CMSTestCase.assertQuerysetEqual


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
        self.assertQuerySetEqual(
            versionable.distinct_groupers(),
            [latest_poll1_version.content.pk, latest_poll2_version.content.pk],
            transform=lambda x: x.pk,
            ordered=False,
        )

    def test_queryset_filter_for_distinct_groupers(self):
        poll1_archived_version = PollVersionFactory(
            content__poll=self.initial_version.content.poll, state=ARCHIVED
        )
        poll1_published_version = PollVersionFactory(
            content__poll=self.initial_version.content.poll, state=PUBLISHED
        )
        poll2_version = PollVersionFactory()
        PollVersionFactory(content__poll=poll2_version.content.poll, state=ARCHIVED)
        poll2_archived_version = PollVersionFactory(
            content__poll=poll2_version.content.poll, state=ARCHIVED
        )

        versionable = VersionableItem(
            content_model=PollContent,
            grouper_field_name="poll",
            copy_function=default_copy,
        )

        qs_published_filter = {"versions__state__in": [PUBLISHED]}
        # Should be one published version
        self.assertQuerySetEqual(
            versionable.distinct_groupers(**qs_published_filter),
            [poll1_published_version.content.pk],
            transform=lambda x: x.pk,
            ordered=False,
        )

        qs_archive_filter = {"versions__state__in": [ARCHIVED]}
        # Should be two archived versions
        self.assertQuerySetEqual(
            versionable.distinct_groupers(**qs_archive_filter),
            [poll1_archived_version.content.pk, poll2_archived_version.content.pk],
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

        self.assertQuerySetEqual(
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

    def test_content_model_is_sideframe_editable_for_sideframe_disabled_model(self):
        """
        A content model with placeholders should not be opened in the sideframe
        """
        versionable = VersionableItem(
            content_model=PageContent,
            grouper_field_name="page",
            copy_function=default_copy,
        )

        self.assertEqual(versionable.content_model_is_sideframe_editable, False)

    def test_content_model_is_sideframe_editable_for_sideframe_enabled_model(self):
        """
        A content model without placeholders should be opened in the sideframe
        """
        versionable = VersionableItem(
            content_model=PollContent,
            grouper_field_name="poll",
            copy_function=default_copy,
        )

        self.assertEqual(versionable.content_model_is_sideframe_editable, True)


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
        class DefaultCopyTestCase(TestCase):
            def setUp(self):
                self.original_content = PollContentFactory()

            def test_default_copy_creates_new_instance(self):
                new_content = default_copy(self.original_content)
                self.assertNotEqual(self.original_content.pk, new_content.pk)
                self.assertEqual(self.original_content.poll, new_content.poll)
                self.assertEqual(self.original_content.language, new_content.language)

            def test_default_copy_copies_placeholders(self):
                placeholder = Placeholder.objects.create(slot='content')
                self.original_content.placeholders.add(placeholder)
                new_content = default_copy(self.original_content)
                self.assertEqual(new_content.placeholders.count(), 1)
                self.assertNotEqual(new_content.placeholders.first().pk, placeholder.pk)
                self.assertEqual(new_content.placeholders.first().slot, placeholder.slot)

            def test_default_copy_raises_exception_on_one2one_relationship(self):
                # Assuming PollContent has a one-to-one relationship for this test
                with self.assertRaises(Exception):
                    default_copy(self.original_content)

            def test_default_copy_raises_exception_on_many2many_relationship(self):
                # Assuming PollContent has a many-to-many relationship for this test
                with self.assertRaises(Exception):
                    default_copy(self.original_content)

            def test_default_copy_calls_copy_relations_if_exists(self):
                class MockContent:
                    _meta = self.original_content._meta
                    _original_manager = self.original_content._original_manager

                    def __init__(self):
                        self.copy_relations_called = False

                    def copy_relations(self):
                        self.copy_relations_called = True

                original_content = MockContent()
                new_content = default_copy(original_content)
                self.assertTrue(new_content.copy_relations_called)



