from cms.test_utils.testcases import CMSTestCase

from django.db import models
from django.test import override_settings

from djangocms_versioning import constants
from djangocms_versioning.models import Version
from djangocms_versioning.test_utils import factories


class DeletionTestCase1(CMSTestCase):
    @override_settings(DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS=False)
    def test_deletion_not_possible(self):
        poll = factories.PollFactory()
        version1 = factories.PollVersionFactory(
            content__poll=poll,
            content__language="en",
        )
        pk1 = version1.pk
        # Now publish and then edit redirect to create a draft on top of published version
        version1.publish(user=self.get_superuser())
        self.assertEqual(Version.objects.get(pk=pk1).state, constants.PUBLISHED)

        version2 = version1.copy(created_by=self.get_superuser())
        version2.save()

        # Check of source field is set
        self.assertIsNotNone(version2.source)

        # try deleting and see if error is raised
        self.assertRaises(models.deletion.ProtectedError,
                          Version.objects.get(pk=pk1).content.delete)


@override_settings(DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS=True)
class DeletionTestCase2(CMSTestCase):

    def test_deletion_possible(self):
        poll = factories.PollFactory()
        version1 = factories.PollVersionFactory(
            content__poll=poll,
            content__language="en",
        )
        pk1 = version1.pk
        # Now publish and then edit redirect to create a draft on top of published version
        version1.publish(user=self.get_superuser())
        self.assertEqual(Version.objects.get(pk=pk1).state, constants.PUBLISHED)

        version2 = version1.copy(created_by=self.get_superuser())
        version2.save()

        # Check of source field is set
        self.assertIsNotNone(version2.source)

        # try deleting and see if error is raised
        Version.objects.get(pk=pk1).content.delete()
        self.assertIsNone(Version.objects.get(pk=version2.pk).source)
