from unittest.mock import Mock, patch

from django.apps import apps
from django.utils.timezone import now

from cms.test_utils.testcases import CMSTestCase

from freezegun import freeze_time

from djangocms_versioning.constants import DRAFT, PUBLISHED
from djangocms_versioning.datastructures import VersionableItem, default_copy
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


class TestVersionModelProperties(CMSTestCase):

    def test_versionable(self):
        version = factories.PollVersionFactory()
        self.assertEqual(version.versionable, PollsCMSConfig.versioning[0])

    def test_grouper(self):
        version = factories.PollVersionFactory()
        self.assertEqual(version.grouper, version.content.poll)
