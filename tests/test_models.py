from mock import Mock, patch

from django.db.models import Q
from django.utils.timezone import now

from cms.test_utils.testcases import CMSTestCase

from freezegun import freeze_time

from djangocms_versioning.constants import DRAFT
from djangocms_versioning.datastructures import VersionableItem
from djangocms_versioning.models import Version
from djangocms_versioning.test_utils import factories
from djangocms_versioning.test_utils.relationships import models


class CopyTestCase(CMSTestCase):

    @freeze_time(None)
    def test_new_version_object_gets_created(self):
        with freeze_time('2017-07-07'):
            # Make sure created in the past
            original_version = factories.PollVersionFactory()
        new_version = original_version.copy()

        # Created a new version record
        self.assertNotEqual(original_version.pk, new_version.pk)
        self.assertEqual(new_version.created, now())
        self.assertEqual(new_version.state, DRAFT)

    def test_content_object_gets_duplicated(self):
        original_version = factories.PollVersionFactory()
        new_version = original_version.copy()

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


class CustomCopyTestCase(CMSTestCase):

    def test_defining_copy_method_for_1to1_works(self):
        old_version = factories.one2one()
        new_rel = models.OneToOneF.objects.create()
        versionable = VersionableItem(
            content_model=models.Content1to1F,
            grouper_field_name='grouper',
            copy_functions={
                'rel': lambda old_content: new_rel
            }
        )
        versionables_mock = Mock(cms_extension=Mock(
            versionables_by_content={models.Content1to1F: versionable}))

        with patch('djangocms_versioning.models.apps.get_app_config') as app_mock:
            app_mock.return_value = versionables_mock
            new_version = old_version.copy()

        self.assertEqual(new_version.content.rel.pk, new_rel.pk)

    def test_defining_copy_method_for_1to1_reverse_works(self):
        old_version = factories.one2one_reverse()
        def copy_function(old_obj, new_obj):
            models.OneToOneB.objects.create(rel=new_obj)
        versionable = VersionableItem(
            content_model=models.Content1to1B,
            grouper_field_name='grouper',
            copy_functions={'onetooneb.rel': copy_function}
        )
        versionables_mock = Mock(cms_extension=Mock(
            versionables_by_content={models.Content1to1B: versionable}))

        with patch('djangocms_versioning.models.apps.get_app_config') as app_mock:
            app_mock.return_value = versionables_mock
            new_version = old_version.copy()

        new_rel = models.OneToOneB.objects.get()
        self.assertEqual(new_rel.rel.pk, new_version.content.pk)

    def test_defining_copy_method_for_1tomany_works(self):
        old_version = factories.one2many()
        new_rel = models.OneToManyF.objects.create()
        versionable = VersionableItem(
            content_model=models.Content1toManyF,
            grouper_field_name='grouper',
            copy_functions={
                'rel': lambda old_content: new_rel
            }
        )
        versionables_mock = Mock(cms_extension=Mock(
            versionables_by_content={models.Content1toManyF: versionable}))

        with patch('djangocms_versioning.models.apps.get_app_config') as app_mock:
            app_mock.return_value = versionables_mock
            new_version = old_version.copy()

        self.assertEqual(new_version.content.rel.pk, new_rel.pk)

    def test_defining_copy_method_for_m2m_works(self):
        old_version = factories.many2many()
        new_rel = models.ManyToManyF.objects.create()
        versionable = VersionableItem(
            content_model=models.ContentManytoManyF,
            grouper_field_name='grouper',
            copy_functions={
                'rel': lambda old_obj, new_obj: new_obj.rel.add(new_rel)
            }
        )
        versionables_mock = Mock(cms_extension=Mock(
            versionables_by_content={models.ContentManytoManyF: versionable}))

        with patch('djangocms_versioning.models.apps.get_app_config') as app_mock:
            app_mock.return_value = versionables_mock
            new_version = old_version.copy()

        self.assertQuerysetEqual(
            new_version.content.rel.all(),
            [new_rel.pk],
            lambda x: x.pk
        )
