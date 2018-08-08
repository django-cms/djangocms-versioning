from django import forms

from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.forms import grouper_form_factory
from djangocms_versioning.test_utils import factories
from djangocms_versioning.test_utils.polls.models import PollContent


class GrouperFormTestCase(CMSTestCase):

    def tearDown(self):
        grouper_form_factory.cache_clear()

    def test_factory(self):
        pv = factories.PollVersionFactory()

        form_class = grouper_form_factory(PollContent)

        self.assertIn(forms.Form, form_class.mro())
        self.assertEqual(form_class.__name__, 'PollContentGrouperForm')
        self.assertIn('grouper', form_class.base_fields)
        self.assertIn(
            (pv.content.poll.pk, str(pv.content.poll)),
            form_class.base_fields['grouper'].choices,
        )

    def test_factory_cache(self):
        """Test that grouper_form_factory is cached
        and return value is created once."""
        self.assertEqual(
            id(grouper_form_factory(PollContent)),
            id(grouper_form_factory(PollContent)),
        )
