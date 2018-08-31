from unittest.mock import Mock, patch

from django.apps import apps
from django.utils.timezone import now

from cms.test_utils.testcases import CMSTestCase

from freezegun import freeze_time

from djangocms_versioning.constants import DRAFT, PUBLISHED
from djangocms_versioning.datastructures import VersionableItem, default_copy
from djangocms_versioning.models import Version, VersionQuerySet
from djangocms_versioning.test_utils import factories
from djangocms_versioning.test_utils.polls.cms_config import PollsCMSConfig
from djangocms_versioning.test_utils.polls.models import PollContent


class CopyTestCase(CMSTestCase):

    def _create_versionables_mock(self, copy_function):
        """Helper function for mocking the versionables_by_content
        property so that a different copy_function can be specified on
        the polls app.
        """
        versionable = VersionableItem(
            content_model=PollContent,
            grouper_field_name='poll',
            copy_function=copy_function
        )
        return {PollContent: versionable}

    @freeze_time(None)
    def test_new_version_object_gets_created(self):
        """When copying, a new version object should get created
        """
        with freeze_time('2017-07-07'):
            # Make sure created in the past
            original_version = factories.PollVersionFactory(state=PUBLISHED)
        user = factories.UserFactory()

        new_version = original_version.copy(user)

        # Created a new version record
        self.assertNotEqual(original_version.pk, new_version.pk)
        self.assertEqual(new_version.created, now())
        self.assertEqual(new_version.created_by, user)
        # The state should always be DRAFT no matter what the original
        # state was
        self.assertEqual(new_version.state, DRAFT)

    def test_content_object_gets_duplicated_with_default_copy(self):
        """When copying, the new version object should have a new
        related content object. The default copy method will copy all
        content fields (other than the pk) exactly as they were.
        """
        original_version = factories.PollVersionFactory()
        user = factories.UserFactory()
        versioning_app_ext = apps.get_app_config(
            'djangocms_versioning').cms_extension
        versionables_mock = self._create_versionables_mock(default_copy)

        with patch.object(versioning_app_ext, 'versionables_by_content', versionables_mock):
            new_version = original_version.copy(user)

        # Created a new content record
        self.assertNotEqual(
            original_version.content.pk,
            new_version.content.pk,
        )
        # Has the same fields as the original version
        self.assertEqual(
            original_version.content.text,
            new_version.content.text,
        )
        self.assertEqual(
            original_version.content.language,
            new_version.content.language,
        )
        self.assertEqual(
            original_version.content.poll,
            new_version.content.poll,
        )

    def test_the_copy_method_is_configurable(self):
        """When copying, the new version object should have a new
        related content object. How the content object will be
        copied can be configured.
        """
        original_version = factories.PollVersionFactory()
        user = factories.UserFactory()
        new_content = factories.PollContentFactory(
            poll=original_version.content.poll)
        mocked_copy = Mock(return_value=new_content)
        versionables_mock = self._create_versionables_mock(mocked_copy)
        versioning_app_ext = apps.get_app_config(
            'djangocms_versioning').cms_extension

        with patch.object(versioning_app_ext, 'versionables_by_content', versionables_mock):
            new_version = original_version.copy(user)

        self.assertEqual(new_version.content.pk, new_content.pk)

    @freeze_time(None)
    def test_page_content_object_gets_duplicated(self):
        """The implementation of versioning for PageContent correctly
        copies the PageContent object
        """
        with freeze_time('2017-07-07'):
            # Make sure created in the past
            original_version = factories.PageVersionFactory()
        user = factories.UserFactory()

        new_version = original_version.copy(user)

        # Created a new content record
        self.assertNotEqual(
            original_version.content.pk,
            new_version.content.pk,
        )
        # Has the same fields as the original version
        self.assertEqual(
            original_version.content.title,
            new_version.content.title,
        )
        self.assertEqual(
            original_version.content.language,
            new_version.content.language,
        )
        self.assertEqual(
            original_version.content.creation_date,
            new_version.content.creation_date,
        )
        self.assertEqual(
            original_version.content.created_by,
            new_version.content.created_by,
        )
        self.assertEqual(new_version.content.changed_date, now())
        self.assertEqual(
            original_version.content.changed_by,
            new_version.content.changed_by,
        )
        self.assertEqual(
            original_version.content.in_navigation,
            new_version.content.in_navigation,
        )
        self.assertEqual(
            original_version.content.soft_root,
            new_version.content.soft_root,
        )
        self.assertEqual(
            original_version.content.template,
            new_version.content.template,
        )
        self.assertEqual(
            original_version.content.limit_visibility_in_menu,
            new_version.content.limit_visibility_in_menu,
        )
        self.assertEqual(
            original_version.content.xframe_options,
            new_version.content.xframe_options,
        )
        self.assertEqual(
            original_version.content.page,
            new_version.content.page,
        )

    def test_placeholders_are_copied(self):
        """The implementation of versioning for PageContent correctly
        copies placeholders
        """
        original_version = factories.PageVersionFactory()
        original_placeholders = factories.PlaceholderFactory.create_batch(
            2, source=original_version.content)
        original_version.content.placeholders.add(*original_placeholders)
        user = factories.UserFactory()

        new_version = original_version.copy(user)

        new_placeholders = new_version.content.placeholders.all()
        self.assertEqual(new_placeholders.count(), 2)
        self.assertNotEqual(
            new_placeholders[0].pk,
            original_placeholders[0].pk
        )
        self.assertEqual(
            new_placeholders[0].slot,
            original_placeholders[0].slot
        )
        self.assertEqual(
            new_placeholders[0].default_width,
            original_placeholders[0].default_width
        )
        self.assertEqual(
            new_placeholders[0].source,
            new_version.content
        )
        self.assertNotEqual(
            new_placeholders[1].pk,
            original_placeholders[1].pk
        )
        self.assertEqual(
            new_placeholders[1].slot,
            original_placeholders[1].slot
        )
        self.assertEqual(
            new_placeholders[1].default_width,
            original_placeholders[1].default_width
        )
        self.assertEqual(
            new_placeholders[1].source,
            new_version.content
        )

    def test_if_source_field_none_then_set_new_source_field_to_none_also(self):
        """Placeholder.source can be None. In such cases it's probably
        best to retain None rather than assign the new content object.
        """
        original_version = factories.PageVersionFactory()
        original_placeholder = factories.PlaceholderFactory(source=None)
        original_version.content.placeholders.add(original_placeholder)
        user = factories.UserFactory()

        new_version = original_version.copy(user)

        new_placeholder = new_version.content.placeholders.get()
        self.assertIsNone(new_placeholder.source)

    @freeze_time(None)
    def test_text_plugins_are_copied(self):
        """The implementation of versioning for PageContent correctly
        copies text plugins
        """
        original_version = factories.PageVersionFactory()
        placeholder = factories.PlaceholderFactory(
            source=original_version.content)
        original_version.content.placeholders.add(placeholder)
        with freeze_time('2017-07-07'):
            # Make sure created in the past
            original_plugins = factories.TextPluginFactory.create_batch(
                2, placeholder=placeholder)
        user = factories.UserFactory()

        new_version = original_version.copy(user)

        new_plugins = new_version.content.placeholders.get(
            ).cmsplugin_set.all()
        self.assertEqual(new_plugins.count(), 2)
        self.assertNotEqual(
            new_plugins[0].pk,
            original_plugins[0].pk
        )
        self.assertEqual(
            new_plugins[0].language,
            original_plugins[0].language
        )
        self.assertIsNone(new_plugins[0].parent)
        self.assertEqual(
            new_plugins[0].position,
            original_plugins[0].position
        )
        self.assertEqual(
            new_plugins[0].plugin_type,
            original_plugins[0].plugin_type
        )
        self.assertEqual(
            new_plugins[0].djangocms_text_ckeditor_text.body,
            original_plugins[0].djangocms_text_ckeditor_text.body
        )
        self.assertEqual(
            new_plugins[0].creation_date,
            original_plugins[0].creation_date
        )
        self.assertEqual(new_plugins[0].changed_date, now())
        self.assertNotEqual(
            new_plugins[1].pk,
            original_plugins[1].pk
        )
        self.assertEqual(
            new_plugins[1].language,
            original_plugins[1].language
        )
        self.assertIsNone(new_plugins[1].parent)
        self.assertEqual(
            new_plugins[1].position,
            original_plugins[1].position
        )
        self.assertEqual(
            new_plugins[1].plugin_type,
            original_plugins[1].plugin_type
        )
        self.assertEqual(
            new_plugins[1].djangocms_text_ckeditor_text.body,
            original_plugins[1].djangocms_text_ckeditor_text.body
        )
        self.assertEqual(
            new_plugins[1].creation_date,
            original_plugins[1].creation_date
        )
        self.assertEqual(new_plugins[1].changed_date, now())

    def test_copy_plugins_method_used(self):
        original_version = factories.PageVersionFactory()
        placeholder = factories.PlaceholderFactory(
            source=original_version.content)
        original_version.content.placeholders.add(placeholder)
        user = factories.UserFactory()

        with patch('djangocms_versioning.cms_config.Placeholder.copy_plugins') as mocked_copy:
            new_version = original_version.copy(user)

        new_placeholder = new_version.content.placeholders.get()
        mocked_copy.assert_called_once_with(new_placeholder)


class TestVersionModelProperties(CMSTestCase):

    def test_versionable(self):
        version = factories.PollVersionFactory()
        self.assertEqual(version.versionable, PollsCMSConfig.versioning[0])

    def test_grouper(self):
        version = factories.PollVersionFactory()
        self.assertEqual(version.grouper, version.content.poll)


class TestVersionQuerySet(CMSTestCase):

    def test_version_uses_versionqueryset_as_manager(self):
        self.assertEqual(
            Version.objects._queryset_class,
            VersionQuerySet,
        )

    def test_get_for_content(self):
        version = factories.PollVersionFactory()
        self.assertEqual(
            Version.objects.get_for_content(version.content),
            version,
        )

    def test_filter_by_grouper(self):
        poll = factories.PollFactory()
        versions = factories.PollVersionFactory.create_batch(
            2, content__poll=poll)  # same grouper
        factories.PollVersionFactory()  # different grouper
        versionable = PollsCMSConfig.versioning[0]

        versions_for_grouper = Version.objects.filter_by_grouper(
            versionable, poll)

        self.assertQuerysetEqual(
            versions_for_grouper,
            [versions[0].pk, versions[1].pk],
            transform=lambda o: o.pk,
            ordered=False
        )

    def test_filter_by_grouper_doesnt_include_other_content_types(self):
        """Regression test for a bug in which filtering by content_type
        field was missed in the query
        """
        pv = factories.PollVersionFactory(content__id=11)
        factories.BlogPostVersionFactory(content__id=11)
        versionable = PollsCMSConfig.versioning[0]

        versions_for_grouper = Version.objects.filter_by_grouper(
            versionable, pv.content.poll)

        # Only poll version included
        self.assertQuerysetEqual(
            versions_for_grouper,
            [pv.pk],
            transform=lambda o: o.pk,
            ordered=False
        )
