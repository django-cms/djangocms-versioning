from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.helpers import is_latest_version
from djangocms_versioning.test_utils import factories


class TestHelpers(CMSTestCase):
    def test_is_latest_version(self):
        poll_1 = factories.PollFactory()
        language = 'en'

        p1_version_1 = factories.PollVersionFactory(
            content__poll=poll_1, content__language=language)
        self.assertEqual(is_latest_version(p1_version_1.content), True)

        p1_version_2 = factories.PollVersionFactory(
            content__poll=poll_1, content__language=language)
        self.assertEqual(is_latest_version(p1_version_1.content), False)
        self.assertEqual(is_latest_version(p1_version_2.content), True)
