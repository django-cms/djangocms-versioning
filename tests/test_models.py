from django.db.models import Q

from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.models import Version
from djangocms_versioning.test_utils.factories import (
    AnswerFactory,
    CategoryFactory,
    PollContentWithVersionFactory,
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

    def test_fk_related_objects_get_copied_not_duplicated_by_default(self):
        original_answers = AnswerFactory.create_batch(
            2, poll_content=self.initial_version.content)

        new_version = self.initial_version.copy()

        new_answers = new_version.content.answer_set.all()
        # Two answers are attached to the new version
        self.assertEqual(new_version.content.answer_set.count(), 2)
        # These answers are the same ones as on the original version
        self.assertIn(
            new_answers[0].pk, [a.pk for a in original_answers])
        self.assertIn(
            new_answers[1].pk, [a.pk for a in original_answers])
        # The answers' fields have not changed
        self.assertEqual(new_answers[0].text, original_answers[0].text)
        self.assertEqual(new_answers[1].text, original_answers[1].text)

    def test_m2m_related_objects_get_copied_not_duplicated_by_default(self):
        another_content = PollContentWithVersionFactory()
        original_categories = CategoryFactory.create_batch(2)
        self.initial_version.content.categories.add(*original_categories)

        new_version = self.initial_version.copy()

        new_categories = new_version.content.categories.all()
        # Two categories are attached to the new version
        self.assertEqual(new_version.content.categories.count(), 2)
        # These categories are the same ones as on the original version
        self.assertIn(
            new_categories[0].pk, [c.pk for c in original_categories])
        self.assertIn(
            new_categories[1].pk, [c.pk for c in original_categories])
        # The categories' fields have not changed
        self.assertEqual(new_categories[0].name, original_categories[0].name)
        self.assertQuerysetEqual(
            new_categories[0].poll_contents.all(),
            original_categories[0].poll_contents.all(),
            lambda x: x.pk
        )
        self.assertEqual(new_categories[1].name, original_categories[1].name)
        self.assertQuerysetEqual(
            new_categories[1].poll_contents.all(),
            original_categories[1].poll_contents.all(),
            lambda x: x.pk
        )

    def test_can_override_copy_behaviour_per_field(self):
        pass
