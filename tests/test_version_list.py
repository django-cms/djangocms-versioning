from urllib.parse import parse_qs, urlparse

from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.helpers import (
    version_list_url,
    version_list_url_for_grouper,
)
from djangocms_versioning.test_utils import factories


class VersionListUrlsTestCase(CMSTestCase):
    def test_version_list_url(self):
        pv = factories.PollVersionFactory(content__language="en")
        url = version_list_url(pv.content)
        parsed = urlparse(url)
        self.assertEqual(
            parsed.path, "/en/admin/djangocms_versioning/pollcontentversion/"
        )
        self.assertEqual(
            {k: v[0] for k, v in parse_qs(parsed.query).items()},
            {"poll": str(pv.grouper.pk), "language": "en"},
        )

    def test_version_list_url_for_grouper(self):
        pv = factories.PollVersionFactory()
        self.assertEqual(
            version_list_url_for_grouper(pv.grouper),
            f"/en/admin/djangocms_versioning/pollcontentversion/?poll={pv.grouper.pk}",
        )
