from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning import constants
from djangocms_versioning.test_utils import factories
from djangocms_versioning.test_utils.polls.models import PollContent


class TestLatestContentCurrentContent(CMSTestCase):
    def setUp(self):
        poll1 = factories.PollFactory()
        factories.PollVersionFactory(state=constants.PUBLISHED, content__language="de")

        factories.PollVersionFactory(state=constants.ARCHIVED, content__poll=poll1, content__language="de")
        v1 = factories.PollVersionFactory(state=constants.UNPUBLISHED, content__poll=poll1, content__language="de")
        v2 = factories.PollVersionFactory(state=constants.ARCHIVED, content__poll=poll1, content__language="en")
        v3 = factories.PollVersionFactory(state=constants.DRAFT, content__poll=poll1, content__language="en")
        v4 = factories.PollVersionFactory(state=constants.UNPUBLISHED, content__poll=poll1, content__language="fr")

        self.poll = poll1
        self.poll_content1 = v1.content
        self.poll_content2 = v2.content
        self.poll_content3 = v3.content
        self.poll_content4 = v4.content

    def test_latest_content(self):
        """only one version per grouper and grouping field (language) returned."""
        latest_content = PollContent.admin_manager.latest_content(poll=self.poll)
        self.assertEqual(latest_content.count(), 3)
        self.assertIn(self.poll_content1, latest_content)
        self.assertIn(self.poll_content3, latest_content)
        self.assertIn(self.poll_content4, latest_content)

    def test_latest_content_by_language(self):
        """only one version per grouper and grouping field (language) returned. Additional
        filter before or after latest_content() should **not** affect the result."""

        latest_content = PollContent.admin_manager.latest_content().filter(poll=self.poll, language="en")
        self.assertEqual(latest_content.count(), 1)
        self.assertIn(self.poll_content3, latest_content)

        latest_content = PollContent.admin_manager.filter(poll=self.poll, language="en").latest_content()
        self.assertEqual(latest_content.count(), 1)
        self.assertIn(self.poll_content3, latest_content)

        latest_content = PollContent.admin_manager.latest_content().filter(poll=self.poll, language="de")
        self.assertEqual(latest_content.count(), 1)
        self.assertIn(self.poll_content1, latest_content)

        latest_content = PollContent.admin_manager.filter(poll=self.poll, language="de").latest_content()
        self.assertEqual(latest_content.count(), 1)
        self.assertIn(self.poll_content1, latest_content)

