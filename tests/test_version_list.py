from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.helpers import (
    version_list_url,
    version_list_url_for_grouper,
)
from djangocms_versioning.test_utils import factories


class VersionListUrlsTestCase(CMSTestCase):

    def test_version_list_url(self):
        pv = factories.PollVersionFactory()
        self.assertEqual(
            version_list_url(pv.content),
            "/en/admin/djangocms_versioning/pollcontentversion/?poll=1",
        )

    def test_version_list_url_for_grouper(self):
        pv = factories.PollVersionFactory()
        self.assertEqual(
            version_list_url_for_grouper(pv.grouper),
            "/en/admin/djangocms_versioning/pollcontentversion/?poll=1",
        )
