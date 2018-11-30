from datetime import datetime

from django.utils import timezone

from cms.test_utils.testcases import CMSTestCase

from freezegun import freeze_time

from djangocms_versioning.models import Version
from djangocms_versioning.test_utils import factories


class HandlersTestCase(CMSTestCase):

    def test_modified_date(self):
        pv = factories.PollVersionFactory()
        dt = datetime(2016, 6, 6, tzinfo=timezone.utc)
        with freeze_time(dt):
            pv.content.save()
        pv = Version.objects.get(pk=pv.pk)
        self.assertEqual(pv.modified, dt)
