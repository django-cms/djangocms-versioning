from django import forms

from cms.models import PageContent, PageUrl
from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.forms import grouper_form_factory
from djangocms_versioning.test_utils import factories
from djangocms_versioning.test_utils.polls.models import PollContent


class GrouperFormTestCase(CMSTestCase):
    def tearDown(self):
        grouper_form_factory.cache_clear()

    def test_factory(self):
        pv = factories.PollVersionFactory()
        form_class = grouper_form_factory(PollContent, language="en")

        self.assertIn(forms.Form, form_class.mro())
        self.assertEqual(form_class.__name__, "PollContentGrouperForm")
        self.assertIn("poll", form_class.base_fields)
        self.assertIn(
            (pv.content.poll.pk, str(pv.content.poll)),
            form_class.base_fields["poll"].choices,
        )

    def test_factory_cache(self):
        """Test that grouper_form_factory is cached
        and return value is created once."""
        self.assertEqual(
            id(grouper_form_factory(PollContent, language="en")),
            id(grouper_form_factory(PollContent, language="en")),
        )

    def test_grouper_selector_default_label(self):
        """
        Grouper selector shows the default label format when no override is set
        """
        version = factories.PollVersionFactory()
        form_class = grouper_form_factory(PollContent, language="en")

        self.assertIn(
            (version.content.poll.pk, str(version.content.poll)),
            form_class.base_fields["poll"].choices,
        )

    def test_grouper_selector_non_default_label_unpublished(self):
        """
        Grouper selector shows the PageContent label format when PageContent is set

        Because PublishedContentManager filters out draft content the label is not
        str(version.content.title) but "No available title"
        """
        version = factories.PageVersionFactory()
        form_class = grouper_form_factory(PageContent, version.content.language)
        label = "{} ({})".format("No available title", "Unpublished")

        choices = list(form_class.base_fields["page"].choices)
        self.assertIn((version.content.page.pk, label), choices)

    def test_grouper_selector_non_default_label(self):
        """
        Grouper selector shows the PageContent label format when PageContent is set
        """
        version = factories.PageVersionFactory()
        PageUrl.objects.create(
            page=version.content.page,
            language=version.content.language,
            path="test",
            slug="test",
        )
        version.publish(version.created_by)
        form_class = grouper_form_factory(PageContent, version.content.language)
        label = "{title} (/{path}/)".format(
            title=version.content.title,
            path=version.content.page.get_path(version.content.language),
        )
        self.assertIn(
            (version.content.page.pk, label), form_class.base_fields["page"].choices
        )
