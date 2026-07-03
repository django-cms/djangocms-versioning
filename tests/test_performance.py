"""
Performance tests for djangocms-versioning to catch N+1 query issues.

These tests use Django's query logging to detect excessive database queries.
"""
from django.db import connection, reset_queries
from django.test import TestCase

from djangocms_versioning.admin import ExtendedVersionAdminMixin
from djangocms_versioning.cms_toolbars import VersioningToolbar
from djangocms_versioning.indicators import content_indicator
from djangocms_versioning.models import Version
from djangocms_versioning.test_utils.factories import (
    PageContentWithVersionFactory,
    PageFactory,
    PollContentWithVersionFactory,
    PollFactory,
    UserFactory,
)


class QueryCountAssertionError(AssertionError):
    """Custom exception for query count assertions."""
    pass


class PerformanceTestMixin:
    """Mixin with helper methods for performance testing."""

    MAX_QUERIES = None  # Override in child classes

    def setUp(self):
        super().setUp()
        # Reset query log before each test
        reset_queries()

    def assertQueryCountLessThan(self, max_queries, message=None):
        """Assert that the number of queries is less than max_queries."""
        query_count = len(connection.queries)
        if message is None:
            message = f"Expected fewer than {max_queries} queries, but got {query_count}"
        self.assertLess(query_count, max_queries, message)

    def assertQueryCount(self, expected_count, message=None):
        """Assert exact query count."""
        query_count = len(connection.queries)
        if message is None:
            message = f"Expected {expected_count} queries, but got {query_count}"
        self.assertEqual(query_count, expected_count, message)

    def get_query_count(self):
        """Return the current query count."""
        return len(connection.queries)


class ToolbarPerformanceTestCase(PerformanceTestMixin, TestCase):
    """Test performance of toolbar methods."""

    MAX_QUERIES = None

    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.poll = PollFactory()
        # PollContentWithVersionFactory automatically creates a version via post_generation
        self.poll_content = PollContentWithVersionFactory(poll=self.poll, language="en", version__created_by=self.user)
        # Get the version that was created
        from djangocms_versioning.models import Version
        self.version = Version.objects.get_for_content(self.poll_content)

    def _create_toolbar(self, obj, edit_mode=False, user=None):
        """Helper to create a toolbar with the given object."""
        from cms.toolbar.toolbar import CMSToolbar

        if user is None:
            user = self.user

        # Create a proper mock request object
        request = type("Request", (), {
            "user": user,
            "GET": {},
            "path": "/test/",
            "path_info": "/test/",
            "META": {"HTTP_HOST": "testserver"},
        })()

        # Create the base toolbar
        cms_toolbar = CMSToolbar(request=request, request_path="/test/")
        cms_toolbar.obj = obj
        cms_toolbar.edit_mode_active = edit_mode
        cms_toolbar.preview_mode_active = False

        # Create the versioning toolbar with proper arguments
        versioning_toolbar = VersioningToolbar(
            request, toolbar=cms_toolbar, is_current_app=True, app_path="/"
        )
        return versioning_toolbar

    def test_toolbar_version_lookups_not_n_plus_1(self):
        """
        Test that toolbar methods don't cause N+1 queries when accessing versions.

        This test checks that multiple calls to Version.objects.get_for_content()
        in the toolbar don't result in excessive queries.
        """
        toolbar = self._create_toolbar(self.poll_content, edit_mode=True)

        # Reset query count
        reset_queries()

        # Call multiple toolbar methods that access versions
        # Each should reuse cached lookups, not query the DB repeatedly
        toolbar._add_publish_button()
        toolbar._add_edit_button()
        toolbar._add_unlock_button()
        toolbar._add_revert_button()
        toolbar._add_versioning_menu()
        toolbar._add_lock_message()

        # With the current implementation, each method calls Version.objects.get_for_content()
        # This should ideally be cached to avoid N+1
        # Expected: 1 query for version lookup (if cached) + some for related objects
        # Actual: 5+ queries (one per method that accesses version)
        query_count = self.get_query_count()

        # This will fail with current implementation
        # Each _add_*_button method calls Version.objects.get_for_content()
        # That's at least 5 separate queries for version lookup alone
        self.assertLess(
            query_count,
            10,  # Allow some margin for other queries
            f"Too many queries ({query_count}) detected in toolbar methods. "
            "Version lookups should be cached to avoid N+1 queries."
        )

    def test_toolbar_with_multiple_objects_no_n_plus_1(self):
        """
        Test that processing multiple content objects in toolbars doesn't cause N+1.
        """
        # Create multiple content objects
        poll2 = PollFactory()
        poll_content2 = PollContentWithVersionFactory(poll=poll2, language="en", version__created_by=self.user)

        poll3 = PollFactory()
        poll_content3 = PollContentWithVersionFactory(poll=poll3, language="en", version__created_by=self.user)

        reset_queries()

        # Process each content object with toolbar
        # This simulates what happens when rendering toolbars for multiple items
        for content in [self.poll_content, poll_content2, poll_content3]:
            toolbar = self._create_toolbar(content, edit_mode=True)
            toolbar._add_publish_button()
            toolbar._add_edit_button()

        query_count = self.get_query_count()

        # With N+1, we'd see 3 objects * 2 methods * 1 query each = 6 queries minimum
        # Plus additional queries for each method
        # This should be much less with proper caching
        self.assertLess(
            query_count,
            15,  # Allow some margin
            f"Too many queries ({query_count}) when processing multiple objects. "
            "Suggests N+1 query issue."
        )


class MenuPerformanceTestCase(PerformanceTestMixin, TestCase):
    """Test performance of menu rendering."""

    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        # Create pages with content
        self.pages = []
        self.page_contents = []
        for _ in range(5):
            page = PageFactory()
            page_content = PageContentWithVersionFactory(page=page, language="en", version__created_by=self.user)
            self.pages.append(page)
            self.page_contents.append(page_content)

    def test_menu_rendering_no_n_plus_1(self):
        """
        Test that menu rendering doesn't cause N+1 queries.

        This specifically tests cms_menus.py where version lookups happen in a loop.
        """
        from djangocms_versioning import conf

        # Skip test if menu registration is not enabled
        if not conf.ENABLE_MENU_REGISTRATION:
            self.skipTest("Menu registration is not enabled")

        from django.contrib.sites.models import Site

        from djangocms_versioning.cms_menus import CMSMenu

        site = Site.objects.get_current()
        user = UserFactory()
        reset_queries()

        # Create menu and get nodes
        request = type("Request", (), {
            "user": user,
            "site": site,
            "request_language": "en",
            "GET": {},
            "path": "/test/",
            "path_info": "/test/",
            "META": {"HTTP_HOST": "testserver"},
        })()
        menu = CMSMenu(request)

        # This will trigger the get_nodes method which processes all page contents
        # The current implementation at line 128 does: version = page_content.versions.all()[0]
        # If versions are not properly prefetched, this causes N+1
        menu.get_nodes(request)

        query_count = self.get_query_count()

        # With 5 pages, if there's N+1, we'd see 5+ queries for version lookups
        # plus the initial queries for pages and content
        # This is a simplified test - the actual menu rendering is more complex
        # but the principle holds
        self.assertLess(
            query_count,
            20,  # Allow margin for initial setup
            f"Too many queries ({query_count}) in menu rendering. "
            "Check cms_menus.py line 128 for N+1 issue."
        )


class IndicatorPerformanceTestCase(PerformanceTestMixin, TestCase):
    """Test performance of indicator functions."""

    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.poll = PollFactory()
        self.poll_content = PollContentWithVersionFactory(poll=self.poll, language="en", version__created_by=self.user)
        from djangocms_versioning.models import Version
        self.version = Version.objects.get_for_content(self.poll_content)

    def test_content_indicator_no_n_plus_1(self):
        """
        Test that content_indicator doesn't cause excessive queries.

        This tests indicators.py line 105-107 where Version.objects.filter_by_content_grouping_values
        is called, which could cause N+1 if called repeatedly.
        """
        reset_queries()

        # Call content_indicator multiple times
        for _ in range(3):
            content_indicator(self.poll_content)

        query_count = self.get_query_count()

        # Each call to content_indicator with versions=None will query the DB
        # With 3 calls, we'd expect 3 queries minimum (N+1 pattern)
        # This should ideally cache the result
        self.assertLess(
            query_count,
            5,  # Allow some margin
            f"Too many queries ({query_count}) when calling content_indicator multiple times. "
            "Result should be cached."
        )

    def test_indicator_with_prefetched_versions(self):
        """
        Test that content_indicator uses prefetched versions when available.
        """
        from djangocms_versioning.models import Version

        reset_queries()

        # Manually prefetch versions - use different polls to avoid unique constraint
        poll_contents = []
        for _ in range(3):
            p = PollFactory()
            pc = PollContentWithVersionFactory(poll=p, language="en", version__created_by=self.user)
            poll_contents.append(pc)

        # Prefetch versions for all
        prefetched = list(Version.objects.filter(
            content_type__model="polls__pollcontent",
            object_id__in=[pc.id for pc in poll_contents]
        ).order_by("-pk"))

        # Attach prefetched versions to each content
        for _, content in enumerate(poll_contents):
            content._prefetched_versions = [v for v in prefetched if v.object_id == content.id]

        reset_queries()

        # Now call content_indicator - it should use prefetched versions
        for content in poll_contents:
            if hasattr(content, "_prefetched_versions") and content._prefetched_versions:
                # This should NOT hit the DB
                content_indicator(content, versions=content._prefetched_versions)

        query_count = self.get_query_count()

        # With prefetched versions, we should see 0 additional queries
        self.assertEqual(
            query_count,
            0,
            f"Expected 0 queries when using prefetched versions, but got {query_count}."
        )


class AdminPerformanceTestCase(PerformanceTestMixin, TestCase):
    """Test performance of admin list display."""

    def setUp(self):
        super().setUp()
        self.user = UserFactory(is_staff=True, is_superuser=True)

        # Create multiple poll contents with versions
        self.poll_contents = []
        for _ in range(10):
            poll = PollFactory()
            poll_content = PollContentWithVersionFactory(poll=poll, language="en", version__created_by=self.user)
            self.poll_contents.append(poll_content)

    def test_admin_list_display_no_n_plus_1(self):
        """
        Test that admin list display doesn't cause N+1 queries.

        This tests the ExtendedVersionAdminMixin methods that access versions
        for each object in the list display.
        """
        from django.contrib import admin as django_admin
        from django.contrib.admin.sites import AdminSite
        from django.test import RequestFactory

        # Create a mock admin class that properly inherits from ModelAdmin
        class TestAdmin(ExtendedVersionAdminMixin, django_admin.ModelAdmin):
            model = PollContentWithVersionFactory._meta.model
            list_display = ["get_versioning_state", "get_author", "get_modified_date"]

        admin = TestAdmin(PollContentWithVersionFactory._meta.model, AdminSite())

        # Build a realistic request so get_queryset exercises the actual admin path
        request = RequestFactory().get("/")
        request.user = self.user

        reset_queries()

        # Get the queryset (this should include prefetching)
        queryset = admin.get_queryset(request)

        # Force evaluation
        content_list = list(queryset)

        query_count_after_queryset = self.get_query_count()

        # Now simulate list display rendering
        for obj in content_list:
            # These methods are called for each row in the admin list
            admin.get_versioning_state(obj)
            admin.get_author(obj)
            admin.get_modified_date(obj)

        total_queries = self.get_query_count()

        # The initial queryset might take a few queries
        # But the list display methods should not add N queries for N objects
        # With 10 objects, if we have N+1, we'd see 10+ additional queries
        additional_queries = total_queries - query_count_after_queryset

        self.assertLess(
            additional_queries,
            5,  # Allow small constant number of additional queries
            f"Too many additional queries ({additional_queries}) when rendering list display "
            f"for {len(content_list)} objects. Suggests N+1 query issue in admin list display methods."
        )


class ModelPerformanceTestCase(PerformanceTestMixin, TestCase):
    """Test performance of model methods."""

    def setUp(self):
        super().setUp()
        self.user = UserFactory()

    def test_version_save_no_n_plus_1(self):
        """
        Test that Version.save() doesn't cause N+1 queries when archiving other drafts.

        Note: We can't easily test this with the factory pattern due to unique constraints.
        The Version model has unique_together = ("content_type", "object_id"), meaning
        only one version per content object. So we test with a different scenario.
        """
        from djangocms_versioning.models import Version

        poll = PollFactory()
        poll_content1 = PollContentWithVersionFactory(poll=poll, language="en", version__created_by=self.user)
        version1 = Version.objects.get_for_content(poll_content1)

        # Create another content with same grouper (poll) but different language
        poll_content2 = PollContentWithVersionFactory(poll=poll, language="fr", version__created_by=self.user)
        Version.objects.get_for_content(poll_content2)

        reset_queries()

        # Save version1 - this might trigger queries for related content
        version1.save()

        query_count = self.get_query_count()

        # The save should not cause excessive queries
        self.assertLess(
            query_count,
            10,
            f"Too many queries ({query_count}) in Version.save()."
        )

    def test_version_publish_no_n_plus_1(self):
        """
        Test that Version.publish() doesn't cause N+1 queries when unpublishing others.

        Note: We create multiple poll contents with the same poll (grouper) but different languages
        to test the unpublishing of other versions in the same group.
        """
        poll = PollFactory()

        # Create first content with a version in draft state
        poll_content1 = PollContentWithVersionFactory(
            poll=poll, language="en", version__created_by=self.user, version__state="draft"
        )
        version1 = Version.objects.get_for_content(poll_content1)

        # Create second content with a version in published state (same poll, different language)
        poll_content2 = PollContentWithVersionFactory(
            poll=poll, language="fr", version__created_by=self.user, version__state="published"
        )
        Version.objects.get_for_content(poll_content2)

        reset_queries()

        # Publish version1 - this should unpublish version2 (same grouper)
        version1.publish(self.user)

        query_count = self.get_query_count()

        # Check models.py lines 388-394 for the unpublish logic
        # The publish method queries for versions to unpublish and then unpublishes them
        # This should be efficient without N+1 queries
        self.assertLess(
            query_count,
            15,
            f"Too many queries ({query_count}) in Version.publish()."
        )


# Run tests with: python -m pytest tests/test_performance.py -v
