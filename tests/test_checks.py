from cms.models.fields import PlaceholderRelationField
from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.constants import (
    ARCHIVED,
    DRAFT,
    PUBLISHED,
    UNPUBLISHED,
)
from djangocms_versioning.helpers import is_content_editable
from djangocms_versioning.test_utils.factories import (
    FancyPollFactory,
    PageVersionFactory,
    PlaceholderFactory,
)


class CheckDraftEditableTestCase(CMSTestCase):
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

    def test_check_unversioned_model(self):
        user = self.get_superuser()
        placeholder = PlaceholderFactory(source=FancyPollFactory())
        self.assertTrue(is_content_editable(placeholder, user))


class CheckInjectTestCase(CMSTestCase):
    def test_draft_state_check_is_injected_into_default_checks(self):
        self.assertIn(is_content_editable, PlaceholderRelationField.default_checks)
