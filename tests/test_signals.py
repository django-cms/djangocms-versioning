from cms.models import PageContent
from cms.test_utils.testcases import CMSTestCase
from cms.test_utils.util.context_managers import signal_tester
from django.dispatch import receiver

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
        version = factories.PollVersionFactory(
            state=constants.DRAFT, content__poll=poll
        )

        with signal_tester(pre_version_operation, post_version_operation) as env:

            version.publish(self.superuser)

            self.assertEqual(env.call_count, 2)

            pre_call_kwargs = env.calls[0][1]
            post_call_kwargs = env.calls[1][1]

            # pre call
            self.assertTrue(pre_call_kwargs["token"] == post_call_kwargs["token"])
            self.assertEqual(pre_call_kwargs["operation"], constants.OPERATION_PUBLISH)
            self.assertEqual(
                pre_call_kwargs["sender"], version.content_type.model_class()
            )
            self.assertEqual(pre_call_kwargs["obj"], version)
            # post call
            self.assertTrue("token" in post_call_kwargs)
            self.assertEqual(post_call_kwargs["operation"], constants.OPERATION_PUBLISH)
            self.assertEqual(
                post_call_kwargs["sender"], version.content_type.model_class()
            )
            self.assertEqual(post_call_kwargs["obj"], version)


    def test_publish_signals_fired_with_to_be_published_and_unpublished(self):
        poll = factories.PollFactory()
        version1 = factories.PollVersionFactory(
            state=constants.DRAFT, content__poll=poll
        )
        version2 = version1.copy(self.superuser)

        # Here, we just expect the signals for version 1
        with signal_tester(pre_version_operation, post_version_operation) as env:
            version1.publish(self.superuser)
            self.assertEqual(env.call_count, 2)

        # Here, we expect the signals for the unpublish of version 1 and the
        # publish of version 2.
        with signal_tester(pre_version_operation, post_version_operation) as env:
            version2.publish(self.superuser)
            self.assertEqual(env.call_count, 4)
            version_1_pre_call_kwargs = env.calls[1][1]
            version_2_post_call_kwargs = env.calls[3][1]

            self.assertEqual(version_1_pre_call_kwargs["to_be_published"], version2)
            self.assertEqual(version_2_post_call_kwargs["unpublished"], [version1])


    def test_unpublish_signals_fired(self):
        """
        When a version is changed to unpublished the correct signals are fired!
        """
        poll = factories.PollFactory()
        version = factories.PollVersionFactory(
            state=constants.PUBLISHED, content__poll=poll
        )

        with signal_tester(pre_version_operation, post_version_operation) as env:

            version.unpublish(self.superuser)

            self.assertEqual(env.call_count, 2)

            pre_call_kwargs = env.calls[0][1]
            post_call_kwargs = env.calls[1][1]

            # pre call
            self.assertTrue(pre_call_kwargs["token"] == post_call_kwargs["token"])
            self.assertEqual(
                pre_call_kwargs["operation"], constants.OPERATION_UNPUBLISH
            )
            self.assertEqual(
                pre_call_kwargs["sender"], version.content_type.model_class()
            )
            self.assertEqual(pre_call_kwargs["obj"], version)
            # post call
            self.assertTrue("token" in post_call_kwargs)
            self.assertEqual(
                post_call_kwargs["operation"], constants.OPERATION_UNPUBLISH
            )
            self.assertEqual(
                post_call_kwargs["sender"], version.content_type.model_class()
            )
            self.assertEqual(post_call_kwargs["obj"], version)

    def test_archive_signals_fired(self):
        """
        When a version is changed to archived the correct signals are fired!
        """
        poll = factories.PollFactory()
        version = factories.PollVersionFactory(
            state=constants.DRAFT, content__poll=poll
        )

        with signal_tester(pre_version_operation, post_version_operation) as env:

            version.archive(self.superuser)

            self.assertEqual(env.call_count, 2)

            pre_call_kwargs = env.calls[0][1]
            post_call_kwargs = env.calls[1][1]

            # pre call
            self.assertTrue(pre_call_kwargs["token"] == post_call_kwargs["token"])
            self.assertEqual(pre_call_kwargs["operation"], constants.OPERATION_ARCHIVE)
            self.assertEqual(
                pre_call_kwargs["sender"], version.content_type.model_class()
            )
            self.assertEqual(pre_call_kwargs["obj"], version)
            # post call
            self.assertTrue("token" in post_call_kwargs)
            self.assertEqual(post_call_kwargs["operation"], constants.OPERATION_ARCHIVE)
            self.assertEqual(
                post_call_kwargs["sender"], version.content_type.model_class()
            )
            self.assertEqual(post_call_kwargs["obj"], version)

    def test_draft_signals_fired(self):
        """
        When a version is set as draft (created) the correct signals are fired!
        """
        poll = factories.PollFactory()

        with signal_tester(pre_version_operation, post_version_operation) as env:

            version = factories.PollVersionFactory(
                state=constants.DRAFT, content__poll=poll
            )

            self.assertEqual(env.call_count, 2)

            pre_call_kwargs = env.calls[0][1]
            post_call_kwargs = env.calls[1][1]

            # pre call
            self.assertTrue(pre_call_kwargs["token"] == post_call_kwargs["token"])
            self.assertEqual(pre_call_kwargs["operation"], constants.OPERATION_DRAFT)
            self.assertEqual(
                pre_call_kwargs["sender"], version.content_type.model_class()
            )
            self.assertEqual(pre_call_kwargs["obj"], version)
            # post call
            self.assertTrue("token" in post_call_kwargs)
            self.assertEqual(post_call_kwargs["operation"], constants.OPERATION_DRAFT)
            self.assertEqual(
                post_call_kwargs["sender"], version.content_type.model_class()
            )
            self.assertEqual(post_call_kwargs["obj"], version)

    def test_page_signals_publish_unpublish_example(self):
        """
        The example in the docs provides the following example to the page publish and unpublish signals.
        """
        signal_hits = []

        # Signal example
        @receiver(post_version_operation, sender=PageContent)
        def do_something_on_page_publish_unpublsh(*args, **kwargs):

            if (
                kwargs["operation"] == constants.OPERATION_PUBLISH
                or kwargs["operation"] == constants.OPERATION_UNPUBLISH
            ):
                # Storing the state of the operation and object at this moment to compare the state later
                obj = {}
                obj["state"] = kwargs["obj"].state
                signal_hits.append(obj)

        version_1 = factories.PageVersionFactory(
            state=constants.DRAFT, content__template=""
        )
        version_2 = factories.PageVersionFactory(
            state=constants.DRAFT, content__template=""
        )
        version_1.publish(self.superuser)
        version_1.unpublish(self.superuser)
        version_2.archive(self.superuser)

        # Only the publish and unpublish signals should have had an affect
        self.assertEqual(len(signal_hits), 2)
        self.assertEqual(signal_hits[0].get("state"), constants.PUBLISHED)
        self.assertEqual(signal_hits[1].get("state"), constants.UNPUBLISHED)
