from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.constants import DRAFT
from djangocms_versioning.models import Version
from djangocms_versioning.test_utils.polls.models import Poll, PollContent


class CheckDraftEditableTestCase(CMSTestCase):
    def test_creation_wo_with_user(self):

        poll = Poll.objects.create(name="my test poll")
        poll_content = PollContent.objects.create(poll=poll, language="en", text="Do you love django CMS?")
        version = Version.objects.create(content=poll_content, created_by=self.get_superuser())
        self.assertEqual(version.state, DRAFT)
        self.assertTrue(poll_content.versions.exists())

    def test_creation_with_user(self):
        poll = Poll.objects.create(name="my test poll")
        user = self.get_superuser()
        poll_content = PollContent.objects\
            .with_user(user=user).create(poll=poll, language="en", text="Do you love django CMS?")
        self.assertTrue(poll_content.versions.exists())
