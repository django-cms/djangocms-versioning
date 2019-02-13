from cms.test_utils.testcases import CMSTestCase
from cms.test_utils.util.context_managers import signal_tester

from djangocms_versioning import constants
from djangocms_versioning.models import Version
from djangocms_versioning.signals import post_version_operation, pre_version_operation
from djangocms_versioning.test_utils import factories


class TestVersioningSignals(CMSTestCase):

    def setUp(self):
        self.superuser = self.get_superuser()

    def test_publish_signals_fired(self):
        """
        When a version is published the correct signals are fired!
        """
        with signal_tester(pre_version_operation, post_version_operation) as env:
            poll = factories.PollFactory()
            version = Version.objects.create(
                content=factories.PollContentFactory(poll=poll, language='en'),
                created_by=factories.UserFactory(),
                state=constants.DRAFT)

            version.publish(self.superuser)

            self.assertEqual(env.call_count, 2)
            self.assertEqual(env.calls[0].obj, version)
            self.assertEqual(env.calls[1].obj, version)

