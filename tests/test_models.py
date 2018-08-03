from freezegun import freeze_time

from django.db.models import Q
from django.utils.timezone import now

from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.constants import DRAFT
from djangocms_versioning.models import Version
from djangocms_versioning.test_utils.factories import (
    AnswerFactory,
    CategoryFactory,
    PollArticleFactory,
    PollContentWithVersionFactory,
    PollExtensionFactory,
    PollVersionFactory,
    SurveyFactory,
    TagFactory,
)


class CopyTestCase(CMSTestCase):

    def setUp(self):
        # Make sure it's an old version
        with freeze_time('2017-07-07'):
            self.initial_version = PollVersionFactory()

    @freeze_time(None)
    def test_new_version_object_gets_created(self):
        new_version = self.initial_version.copy()

        # Created a new version record
        self.assertNotEqual(self.initial_version.pk, new_version.pk)
        self.assertEqual(new_version.created, now())
        self.assertEqual(new_version.state, DRAFT)

    def test_content_object_gets_duplicated(self):
        new_version = self.initial_version.copy()

        # Created a new content record
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

    def test_fk_on_model_get_copied_not_duplicated_by_default(self):
        self.initial_version.content.survey = SurveyFactory()
        self.initial_version.save()

        new_version = self.initial_version.copy()

        # Same survey attached to both versions
        self.assertEqual(
            self.initial_version.content.survey.pk,
            new_version.content.survey.pk
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

    def test_m2m_on_model_gets_copied_not_duplicated_by_default(self):
        # Create tags for the original version
        original_tags = TagFactory.create_batch(2)
        self.initial_version.content.tags.add(*original_tags)
        # This is a m2m so make sure there are other poll contents attached
        another_content1 = PollContentWithVersionFactory()
        another_content2 = PollContentWithVersionFactory()
        original_tags[0].poll_contents.add(another_content1)
        original_tags[1].poll_contents.add(another_content2)

        new_version = self.initial_version.copy()

        new_tags = new_version.content.tags.all()
        # Two tags are attached to the new version
        self.assertEqual(new_version.content.tags.count(), 2)
        # These tags are the same ones as on the original version
        self.assertIn(
            new_tags[0].pk, [c.pk for c in original_tags])
        self.assertIn(
            new_tags[1].pk, [c.pk for c in original_tags])

    def test_m2m_related_objects_get_copied_not_duplicated_by_default(self):
        # Create categories for the original version
        original_categories = CategoryFactory.create_batch(2)
        self.initial_version.content.categories.add(*original_categories)
        # This is a m2m so make sure there are other poll contents attached
        another_content1 = PollContentWithVersionFactory()
        another_content2 = PollContentWithVersionFactory()
        original_categories[0].poll_contents.add(another_content1)
        original_categories[1].poll_contents.add(another_content2)

        new_version = self.initial_version.copy()

        new_categories = new_version.content.categories.all()
        # Two categories are attached to the new version
        self.assertEqual(new_version.content.categories.count(), 2)
        # These categories are the same ones as on the original version
        self.assertIn(
            new_categories[0].pk, [c.pk for c in original_categories])
        self.assertIn(
            new_categories[1].pk, [c.pk for c in original_categories])

    def test_one_to_one_fk_on_model_duplicated_by_default(self):
        self.initial_version.content.poll_extension = PollExtensionFactory()
        self.initial_version.content.save()

        new_version = self.initial_version.copy()

        original_poll_ext = self.initial_version.content.poll_extension
        new_poll_ext = new_version.content.poll_extension
        # The old poll extension and the new poll extension are different
        # objects
        self.assertNotEqual(original_poll_ext.pk, new_poll_ext.pk)
        # The poll extensions have the same fields
        self.assertEqual(
            original_poll_ext.help_text, new_poll_ext.help_text)

    def test_one_to_one_fk_related_object_duplicated_by_default(self):
        original_poll_art = PollArticleFactory(
            poll_content=self.initial_version.content)

        new_version = self.initial_version.copy()

        new_poll_art = new_version.content.pollarticle
        # The old poll article and the new poll article are different
        # objects
        self.assertNotEqual(original_poll_art.pk, new_poll_art.pk)
        # The poll extensions have the same fields
        self.assertEqual(
            original_poll_art.text, new_poll_art.text)

    def test_can_override_copy_behaviour_per_field(self):
        pass


# TODO: Relations on related objects
# TODO: Generic relations
