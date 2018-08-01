from django.db.models import Q

from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.models import Version
from djangocms_versioning.test_utils.factories import (
    AnswerFactory,
    PollVersionFactory,
)


class CopyTestCase(CMSTestCase):

    def setUp(self):
        self.initial_version = PollVersionFactory()

    def test_content_object_gets_duplicated(self):
        new_version = self.initial_version.copy()

        # Created a new record
        self.assertNotEqual(
            self.initial_version.content.pk,
            new_version.content.pk,
        )
        # Has the same fields as the original version
        self.assertEqual(
            self.initial_version.content.text,
            new_version.content.text,
        )
        self.assertEqual(
            self.initial_version.content.language,
            new_version.content.language,
        )
        self.assertEqual(
            self.initial_version.content.poll,
            new_version.content.poll,
        )

    def test_fk_related_objects_get_duplicated(self):
        original_answers = AnswerFactory.create_batch(
            2, poll_content=self.initial_version.content)

        new_version = self.initial_version.copy()

        new_answers = new_version.content.answer_set.all()
        # Two answers are attached to the new version
        self.assertEqual(new_answers.count(), 2)
        # These answers are not the same ones as on the original version
        self.assertNotIn(
            new_answers[0].pk, [a.pk for a in original_answers])
        self.assertNotIn(
            new_answers[1].pk, [a.pk for a in original_answers])
        # The answers have the same field values as the original ones
        self.assertEqual(new_answers[0].text, original_answers[0].text)
        self.assertEqual(new_answers[1].text, original_answers[1].text)

    def test_m2m_related_objects_get_duplicated(self):
        pass

    def test_can_override_copy_behaviour_per_field(self):
        pass
