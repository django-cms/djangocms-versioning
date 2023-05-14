from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning import versionables


class VersionableTestCase(CMSTestCase):
    def test_exists_functions_for_models(self):
        """With the example of the poll app test if versionables exists for models"""
        from djangocms_versioning.test_utils.polls.models import (
            Poll,
            PollContent,
        )

        # Check existence
        self.assertTrue(versionables.exists_for_grouper(Poll))
        self.assertTrue(versionables.exists_for_content(PollContent))

        # Check absence
        self.assertFalse(versionables.exists_for_grouper(PollContent))
        self.assertFalse(versionables.exists_for_content(Poll))

    def test_exists_functions_for_objects(self):
        """With the example of the poll app test if versionables exists for objects"""
        from djangocms_versioning.test_utils.factories import (
            PollContentFactory,
            PollFactory,
        )

        poll = PollFactory()
        poll_content = PollContentFactory(poll=poll)

        # Check existence
        self.assertTrue(versionables.exists_for_grouper(poll))
        self.assertTrue(versionables.exists_for_content(poll_content))

        # Check absence
        self.assertFalse(versionables.exists_for_grouper(poll_content))
        self.assertFalse(versionables.exists_for_content(poll))

    def test_get_versionable(self):
        """With the example of the poll app test if versionables for grouper and content models are the same.
        The versionable correctly identfies the content model."""
        from djangocms_versioning.test_utils.polls.models import (
            Poll,
            PollContent,
        )

        v1 = versionables.for_grouper(Poll)
        v2 = versionables.for_content(PollContent)

        self.assertEqual(v1, v2)  # Those are supposed to return the same versionable
        self.assertEqual(v1.content_model, PollContent)  # PollContent should be the content model

    def test_get_versionable_fails_on_unversioned_models(self):
        from djangocms_versioning.test_utils.text.models import Text

        # Versionables do not exists
        self.assertFalse(versionables.exists_for_grouper(Text))
        self.assertFalse(versionables.exists_for_content(Text))

        # Trying to get them raises error
        self.assertRaises(KeyError, lambda: versionables.for_grouper(Text))
        self.assertRaises(KeyError, lambda: versionables.for_content(Text))
