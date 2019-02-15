from cms.test_utils.testcases import CMSTestCase
from cms.test_utils.util.context_managers import signal_tester

from djangocms_versioning import constants
from djangocms_versioning.signals import (
    post_version_operation,
    pre_version_operation,
)
from djangocms_versioning.test_utils import factories


class TestVersioningSignals(CMSTestCase):

    def setUp(self):
        self.superuser = self.get_superuser()

    def test_publish_signals_fired(self):
        """
        When a version is changed to published the correct signals are fired!
        """
        poll = factories.PollFactory()
        version = factories.PollVersionFactory(state=constants.DRAFT, content__poll=poll)

        with signal_tester(pre_version_operation, post_version_operation) as env:

            version.publish(self.superuser)

            self.assertEqual(env.call_count, 2)

            pre_call_kwargs = env.calls[0][1]
            post_call_kwargs = env.calls[1][1]

            # pre call
            self.assertTrue(pre_call_kwargs['token'] == post_call_kwargs['token'])
            self.assertEqual(pre_call_kwargs['operation'], constants.OPERATION_PUBLISH)
            self.assertEqual(pre_call_kwargs['sender'], version.content_type.model_class())
            self.assertEqual(pre_call_kwargs['obj'], version)
            # post call
            self.assertTrue('token' in post_call_kwargs)
            self.assertEqual(post_call_kwargs['operation'], constants.OPERATION_PUBLISH)
            self.assertEqual(post_call_kwargs['sender'], version.content_type.model_class())
            self.assertEqual(post_call_kwargs['obj'], version)

    def test_unpublish_signals_fired(self):
        """
        When a version is changed to unpublished the correct signals are fired!
        """
        poll = factories.PollFactory()
        version = factories.PollVersionFactory(state=constants.PUBLISHED, content__poll=poll)

        with signal_tester(pre_version_operation, post_version_operation) as env:

            version.unpublish(self.superuser)

            self.assertEqual(env.call_count, 2)

            pre_call_kwargs = env.calls[0][1]
            post_call_kwargs = env.calls[1][1]

            # pre call
            self.assertTrue(pre_call_kwargs['token'] == post_call_kwargs['token'])
            self.assertEqual(pre_call_kwargs['operation'], constants.OPERATION_UNPUBLISH)
            self.assertEqual(pre_call_kwargs['sender'], version.content_type.model_class())
            self.assertEqual(pre_call_kwargs['obj'], version)
            # post call
            self.assertTrue('token' in post_call_kwargs)
            self.assertEqual(post_call_kwargs['operation'], constants.OPERATION_UNPUBLISH)
            self.assertEqual(post_call_kwargs['sender'], version.content_type.model_class())
            self.assertEqual(post_call_kwargs['obj'], version)

    def test_archive_signals_fired(self):
        """
        When a version is changed to archived the correct signals are fired!
        """
        poll = factories.PollFactory()
        version = factories.PollVersionFactory(state=constants.DRAFT, content__poll=poll)

        with signal_tester(pre_version_operation, post_version_operation) as env:

            version.archive(self.superuser)

            self.assertEqual(env.call_count, 2)

            pre_call_kwargs = env.calls[0][1]
            post_call_kwargs = env.calls[1][1]

            # pre call
            self.assertTrue(pre_call_kwargs['token'] == post_call_kwargs['token'])
            self.assertEqual(pre_call_kwargs['operation'], constants.OPERATION_ARCHIVE)
            self.assertEqual(pre_call_kwargs['sender'], version.content_type.model_class())
            self.assertEqual(pre_call_kwargs['obj'], version)
            # post call
            self.assertTrue('token' in post_call_kwargs)
            self.assertEqual(post_call_kwargs['operation'], constants.OPERATION_ARCHIVE)
            self.assertEqual(post_call_kwargs['sender'], version.content_type.model_class())
            self.assertEqual(post_call_kwargs['obj'], version)

    def test_draft_signals_fired(self):
        """
        When a version is set as draft (created) the correct signals are fired!
        """
        poll = factories.PollFactory()

        with signal_tester(pre_version_operation, post_version_operation) as env:

            version = factories.PollVersionFactory(state=constants.DRAFT, content__poll=poll)

            self.assertEqual(env.call_count, 2)

            pre_call_kwargs = env.calls[0][1]
            post_call_kwargs = env.calls[1][1]

            # pre call
            self.assertTrue(pre_call_kwargs['token'] == post_call_kwargs['token'])
            self.assertEqual(pre_call_kwargs['operation'], constants.OPERATION_DRAFT)
            self.assertEqual(pre_call_kwargs['sender'], version.content_type.model_class())
            self.assertEqual(pre_call_kwargs['obj'], version)
            # post call
            self.assertTrue('token' in post_call_kwargs)
            self.assertEqual(post_call_kwargs['operation'], constants.OPERATION_DRAFT)
            self.assertEqual(post_call_kwargs['sender'], version.content_type.model_class())
            self.assertEqual(post_call_kwargs['obj'], version)
