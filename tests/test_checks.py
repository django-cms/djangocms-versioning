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


class NewDraftPropertiesTestCase(CMSTestCase):
    def test_new_draft_properties_set_for_published_placeholder(self):
        """Test that new_draft properties are set on published placeholders"""
        user = self.get_superuser()
        version = PageVersionFactory(state=PUBLISHED)
        placeholder = PlaceholderFactory(source=version.content)

        # Call is_content_editable which should set the new_draft properties
        is_content_editable(placeholder, user)

        # Check that new_draft properties are set
        self.assertTrue(hasattr(placeholder, "new_draft"))
        self.assertTrue(hasattr(placeholder, "new_draft_method"))
        self.assertTrue(hasattr(placeholder, "new_draft_url"))
        self.assertEqual(placeholder.new_draft_method, "cms-form-post-method")
        self.assertIn("edit-redirect", placeholder.new_draft_url)

    def test_new_draft_properties_not_set_for_archived_placeholder(self):
        """Test that new_draft properties are NOT set on archived placeholders"""
        user = self.get_superuser()
        version = PageVersionFactory(state=ARCHIVED)
        placeholder = PlaceholderFactory(source=version.content)

        # Call is_content_editable which should NOT set the new_draft properties for archived
        is_content_editable(placeholder, user)

        # Check that new_draft properties are NOT set
        self.assertFalse(hasattr(placeholder, "new_draft"))
        self.assertFalse(hasattr(placeholder, "new_draft_method"))
        self.assertFalse(hasattr(placeholder, "new_draft_url"))

    def test_new_draft_properties_not_set_for_unpublished_placeholder(self):
        """Test that new_draft properties are NOT set on unpublished placeholders"""
        user = self.get_superuser()
        version = PageVersionFactory(state=UNPUBLISHED)
        placeholder = PlaceholderFactory(source=version.content)

        # Call is_content_editable which should NOT set the new_draft properties for unpublished
        is_content_editable(placeholder, user)

        # Check that new_draft properties are NOT set
        self.assertFalse(hasattr(placeholder, "new_draft"))
        self.assertFalse(hasattr(placeholder, "new_draft_method"))
        self.assertFalse(hasattr(placeholder, "new_draft_url"))

    def test_new_draft_properties_not_set_for_draft_placeholder(self):
        """Test that new_draft properties are NOT set on draft placeholders (already editable)"""
        user = self.get_superuser()
        version = PageVersionFactory(state=DRAFT)
        placeholder = PlaceholderFactory(source=version.content)

        # Call is_content_editable which should NOT set the new_draft properties for drafts
        is_content_editable(placeholder, user)

        # Check that new_draft properties are NOT set (draft is already editable)
        self.assertFalse(hasattr(placeholder, "new_draft"))
        self.assertFalse(hasattr(placeholder, "new_draft_method"))
        self.assertFalse(hasattr(placeholder, "new_draft_url"))
