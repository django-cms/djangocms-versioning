from unittest.mock import patch

from cms.models.contentmodels import PageContent
from cms.test_utils.testcases import CMSTestCase
from django.db import models

from djangocms_versioning import constants, helpers
from djangocms_versioning.helpers import replace_manager
from djangocms_versioning.managers import (
    AdminManagerMixin,
    PublishedContentManagerMixin,
)
from djangocms_versioning.test_utils.factories import (
    PageFactory,
    PageVersionFactory,
)
from djangocms_versioning.test_utils.people.models import Person


class ContentModelTestCase(CMSTestCase):
    def tearDown(self):
        Person.add_to_class("objects", models.Manager())

    def test_replace_default_manager(self):
        self.assertNotIn(PublishedContentManagerMixin, Person.objects.__class__.mro())
        replace_manager(Person, "objects", PublishedContentManagerMixin)
        self.assertIn(PublishedContentManagerMixin, Person.objects.__class__.mro())

        self.assertFalse(hasattr(Person, "admin_manager"))
        replace_manager(Person, "admin_manager", AdminManagerMixin)
        self.assertIn(AdminManagerMixin, Person.admin_manager.__class__.mro())

    def test_replace_default_manager_twice(self):
        replace_manager(Person, "objects", PublishedContentManagerMixin)
        with patch.object(helpers, "manager_factory") as mock:
            replace_manager(Person, "objects", PublishedContentManagerMixin)
        mock.assert_not_called()

        original_manager = Person._original_manager

        replace_manager(Person, "admin_manager", AdminManagerMixin)
        with patch.object(helpers, "manager_factory") as mock:
            replace_manager(Person, "admin_manager", AdminManagerMixin)
        mock.assert_not_called()

        # Replacing admin_manager did not overwrite _original_manager?
        self.assertEqual(Person._original_manager, original_manager)


class AdminManagerTestCase(CMSTestCase):
    def create_page_content(self, page, language, version_state):
        version = PageVersionFactory(content__page=page, content__language=language)
        if version_state == constants.PUBLISHED:
            version.publish(self.get_superuser())
        elif version_state == constants.ARCHIVED:
            version.archive(self.get_superuser())

    def setUp(self) -> None:
        self.pages1 = [PageFactory() for i in range(2)]
        for page in self.pages1:
            self.create_page_content(page, "en", constants.DRAFT)
            self.create_page_content(page, "it", constants.PUBLISHED)

        self.pages2 = [PageFactory() for i in range(2)]
        for page in self.pages2:
            self.create_page_content(page, "en", constants.PUBLISHED)
            self.create_page_content(page, "en", constants.DRAFT)
            self.create_page_content(page, "it", constants.ARCHIVED)
            self.create_page_content(page, "it", constants.PUBLISHED)

    def test_current_content(self):
        # 12 PageContent versions in total
        self.assertEqual(len(list(
            PageContent.admin_manager.all()
        )), 12)

        # 4 total PageContent versions for self.pages1 (2 pages x 2 languages)
        qs = PageContent.admin_manager.filter(page__in=self.pages1)
        self.assertEqual(len(qs), 4)
        self.assertEqual(qs._group_by_key, ["page", "language"])
        self.assertEqual(len(list(
            PageContent.admin_manager.filter(page__in=self.pages1).current_content()
        )), 4, f"{list(PageContent.admin_manager.filter(page__in=self.pages1).current_content())}")
        # 2 current PageContent versions for self.pages2
        self.assertEqual(len(list(
            PageContent.admin_manager.filter(page__in=self.pages2).current_content()
        )), 4)

        # Now unpublish all published in pages2
        for page in self.pages2:
            for content in page.pagecontent_set.all():
                content.versions.first().unpublish(self.get_superuser())

        # 2 current PageContent versions for self.pages2
        self.assertEqual(len(list(
            PageContent.admin_manager.filter(page__in=self.pages2).current_content()
        )), 2)
