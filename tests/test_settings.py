from cms.test_utils.testcases import CMSTestCase
from django.conf import settings
from django.db import models
from django.test import override_settings

from djangocms_versioning import constants, models as versioning_models
from djangocms_versioning.test_utils import factories


class DeletionTestCase(CMSTestCase):
    @override_settings(DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS=False)
    def test_deletion_not_possible(self):
        # Since djangocms_versionings.models stores the setting, we need to update that copy
        versioning_models.ALLOW_DELETING_VERSIONS = settings.DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS
        poll = factories.PollFactory()
        version1 = factories.PollVersionFactory(
            content__poll=poll,
            content__language="en",
        )
        pk1 = version1.pk
        # Now publish and then edit redirect to create a draft on top of published version
        version1.publish(user=self.get_superuser())
        self.assertEqual(versioning_models.Version.objects.get(pk=pk1).state, constants.PUBLISHED)

        version2 = version1.copy(created_by=self.get_superuser())
        version2.save()

        # Check of source field is set
        self.assertIsNotNone(version2.source)

        # try deleting and see if error is raised
        self.assertRaises(models.deletion.ProtectedError,
                          versioning_models.Version.objects.get(pk=pk1).content.delete)

    @override_settings(DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS=True)
    def test_deletion_possible(self):
        # Since djangocms_versionings.models stores the setting, we need to update that copy
        versioning_models.ALLOW_DELETING_VERSIONS = settings.DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS
        poll = factories.PollFactory()
        version1 = factories.PollVersionFactory(
            content__poll=poll,
            content__language="en",
        )
        pk1 = version1.pk
        # Now publish and then edit redirect to create a draft on top of published version
        version1.publish(user=self.get_superuser())
        self.assertEqual(versioning_models.Version.objects.get(pk=pk1).state, constants.PUBLISHED)

        version2 = version1.copy(created_by=self.get_superuser())
        version2.save()

        # Check of source field is set
        self.assertIsNotNone(version2.source)

        # try deleting and see if error is raised
        versioning_models.Version.objects.get(pk=pk1).content.delete()
        self.assertIsNone(versioning_models.Version.objects.get(pk=version2.pk).source)
