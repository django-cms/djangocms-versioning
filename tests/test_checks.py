from cms.models.fields import PlaceholderRelationField
from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.constants import ARCHIVED, DRAFT, PUBLISHED, UNPUBLISHED
from djangocms_versioning.test_utils.factories import (
    PageVersionFactory,
    PlaceholderFactory,
)


from djangocms_versioning.helpers import is_content_editable


class CheckLockTestCase(CMSTestCase):

    def test_check_archived_state(self):
        user = self.get_superuser()
        version = PageVersionFactory(state=ARCHIVED)
        placeholder = PlaceholderFactory(source=version.content)

        self.assertFalse(is_content_editable(placeholder, user))

    def test_check_draft_state(self):
        user = self.get_superuser()
        version = PageVersionFactory(state=DRAFT)
        placeholder = PlaceholderFactory(source=version.content)

        self.assertTrue(is_content_editable(placeholder, user))

    def test_check_unpublished_state(self):
        user = self.get_superuser()
        version = PageVersionFactory(state=UNPUBLISHED)
        placeholder = PlaceholderFactory(source=version.content)

        self.assertFalse(is_content_editable(placeholder, user))

    def test_check_published_state(self):
        user = self.get_superuser()
        version = PageVersionFactory(state=PUBLISHED)
        placeholder = PlaceholderFactory(source=version.content)

        self.assertFalse(is_content_editable(placeholder, user))



    def test_check_locked_for_the_same_user(self):
        user = self.get_superuser()
        version = PageVersionFactory(created_by=user)
        placeholder = PlaceholderFactory(source=version.content)

        self.assertTrue(is_content_editable(placeholder, user))

    def test_check_locked_for_the_other_user(self):
        user1 = self.get_superuser()
        user2 = self.get_standard_user()
        version = PageVersionFactory(created_by=user1)
        placeholder = PlaceholderFactory(source=version.content)

        self.assertFalse(is_content_editable(placeholder, user2))


class CheckInjectTestCase(CMSTestCase):

    def test_lock_check_is_injected_into_default_checks(self):
        self.assertIn(
            is_content_editable,
            PlaceholderRelationField.default_checks,
        )
