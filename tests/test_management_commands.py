from django.core.management import call_command
from django.db import transaction

from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning import constants
from djangocms_versioning.models import Version
from djangocms_versioning.test_utils.blogpost.models import BlogContent, BlogPost
from djangocms_versioning.test_utils.polls.models import Poll, PollContent


class CreateVersionsTestCase(CMSTestCase):
    def test_create_versions(self):
        # blog has no additional grouping field
        structure = dict(en=5, de=2, nl=7)

        # Create BlogPosts w/o version objects
        with transaction.atomic():
            post = BlogPost(name="my multi-lingual blog post")
            post.save()
            for language, cnt in structure.items():
                for i in range(cnt):
                    BlogContent(blogpost=post, language=language).save()
            poll = Poll()
            poll.save()
            for language, cnt in structure.items():
                for i in range(cnt):
                    PollContent(poll=poll, language=language).save()

        self.assertEqual(Version.objects.count(), 0)

        try:
            call_command('create_versions', userid=self.get_superuser().pk, state=constants.DRAFT)
        except SystemExit as e:
            status_code = str(e)
        else:
            # the "no changes" exit code is 0
            status_code = '0'
        self.assertEqual(status_code, '0')

        # Blog has no additional grouping field, i.e. all except the last blog content must be archived
        blog_contents = BlogContent.admin_manager.filter(blogpost=post, language=language).order_by("-pk")
        self.assertEqual(blog_contents[0].versions.first().state, constants.DRAFT)
        for cont in blog_contents[1:]:
            self.assertEqual(cont.versions.first().state, constants.ARCHIVED)

        # Poll has additional grouping field, i.e. for each language there must be one draft (rest archived)
        for language, cnt in structure.items():
            poll_contents = PollContent.admin_manager.filter(poll=poll, language=language).order_by("-pk")
            self.assertEqual(poll_contents[0].versions.first().state, constants.DRAFT)
            for cont in poll_contents[1:]:
                self.assertEqual(cont.versions.first().state, constants.ARCHIVED)
