from freezegun import freeze_time

from django.db.models import Q
from django.utils.timezone import now

from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.constants import DRAFT
from djangocms_versioning.models import Version
from djangocms_versioning.test_utils import factories


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
