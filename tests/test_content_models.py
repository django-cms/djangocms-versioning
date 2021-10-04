from unittest.mock import patch

from django.db import models

from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning import helpers
from djangocms_versioning.helpers import replace_default_manager
from djangocms_versioning.managers import PublishedContentManagerMixin
from djangocms_versioning.test_utils.people.models import Person


class ContentModelTestCase(CMSTestCase):
    def tearDown(self):
        Person.add_to_class("objects", models.Manager())

    def test_replace_default_manager(self):
        self.assertNotIn(PublishedContentManagerMixin, Person.objects.__class__.mro())
        replace_default_manager(Person)
        self.assertIn(PublishedContentManagerMixin, Person.objects.__class__.mro())

    def test_replace_default_manager_twice(self):
        replace_default_manager(Person)

        with patch.object(helpers, "published_content_manager_factory") as mock:
            replace_default_manager(Person)

        mock.assert_not_called()
