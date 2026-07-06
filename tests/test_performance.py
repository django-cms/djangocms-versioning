"""
Performance tests for djangocms-versioning to catch N+1 query issues.

Query counts are measured with Django's ``assertNumQueries`` and
``CaptureQueriesContext``. These force a debug cursor and therefore count
reliably regardless of ``settings.DEBUG`` -- the test runner forces
``DEBUG=False``, so ``connection.queries`` would otherwise stay empty and every
assertion would pass vacuously.
"""
from contextlib import contextmanager
from unittest import skipIf

from django.contrib import admin as django_admin
from django.contrib.admin.sites import AdminSite
from django.contrib.sites.models import Site
from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext

from djangocms_versioning import conf
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


class PerformanceTestMixin:
    """Helpers for asserting on the number of database queries."""

    @contextmanager
    def assertMaxQueries(self, max_queries, msg=None):
        """Assert the wrapped block runs at most ``max_queries`` queries.

        Uses ``CaptureQueriesContext`` (which forces a debug cursor) so the count
        is correct even though the test runner sets ``DEBUG=False``.
        """
        with CaptureQueriesContext(connection) as ctx:
            yield ctx
        count = len(ctx.captured_queries)
        if count > max_queries:
            sql = "\n".join(q["sql"] for q in ctx.captured_queries)
            self.fail(msg or f"Expected at most {max_queries} queries, got {count}:\n{sql}")


class ToolbarPerformanceTestCase(PerformanceTestMixin, TestCase):
    """Test that the toolbar caches its version lookup instead of re-querying."""

    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.poll = PollFactory()
        # PollContentWithVersionFactory creates a version via post_generation.
        self.poll_content = PollContentWithVersionFactory(
            poll=self.poll, language="en", version__created_by=self.user
        )

    def _create_toolbar(self, obj, edit_mode=False, user=None):
        """Helper to create a toolbar with the given object."""
        from cms.toolbar.toolbar import CMSToolbar

        if user is None:
            user = self.user

        request = type("Request", (), {
            "user": user,
            "GET": {},
            "path": "/test/",
            "path_info": "/test/",
            "META": {"HTTP_HOST": "testserver"},
        })()

        cms_toolbar = CMSToolbar(request=request, request_path="/test/")
        cms_toolbar.obj = obj
        cms_toolbar.edit_mode_active = edit_mode
        cms_toolbar.preview_mode_active = False

        return VersioningToolbar(
            request, toolbar=cms_toolbar, is_current_app=True, app_path="/"
        )

    @staticmethod
    def _clear_version_cache(obj):
        """Drop cached versions so the object mirrors a freshly loaded instance."""
        for attr in ("_version_cache", "_prefetched_versions", "_latest_draft_version"):
            if hasattr(obj, attr):
                delattr(obj, attr)

    def test_toolbar_caches_version_lookup(self):
        """The toolbar looks the version up once and reuses it (no N+1).

        ``_get_version`` is called by every button/message helper; it must query
        the database only on the first call and serve the cache afterwards.
        """
        self._clear_version_cache(self.poll_content)
        toolbar = self._create_toolbar(self.poll_content, edit_mode=True)

        with self.assertNumQueries(1):
            for _ in range(5):
                toolbar._get_version()

    def test_toolbar_multiple_objects_one_query_each(self):
        """Rendering several objects costs one version query per object, not N+1.

        Each object legitimately needs its own lookup, but a single object must
        never be queried more than once.
        """
        contents = [self.poll_content]
        for _ in range(2):
            poll = PollFactory()
            contents.append(
                PollContentWithVersionFactory(poll=poll, language="en", version__created_by=self.user)
            )
        for content in contents:
            self._clear_version_cache(content)

        # Exactly one version query per object (reused within each toolbar), no N+1.
        # Count version-table queries only, ignoring incidental framework lookups
        # (e.g. a one-off django_site query when the first toolbar is built).
        with CaptureQueriesContext(connection) as ctx:
            for content in contents:
                toolbar = self._create_toolbar(content, edit_mode=True)
                toolbar._get_version()
                toolbar._get_version()

        version_queries = [
            q for q in ctx.captured_queries
            if "djangocms_versioning_version" in q["sql"]
        ]
        self.assertEqual(
            len(version_queries),
            len(contents),
            f"Expected one version query per object ({len(contents)}), got "
            f"{len(version_queries)}; suggests an N+1 in the toolbar version lookup.",
        )


class MenuPerformanceTestCase(PerformanceTestMixin, TestCase):
    """Test that menu rendering prefetches versions instead of an N+1 loop."""

    @skipIf(conf.ENABLE_MENU_REGISTRATION, "Only with menu registration enabled")
    def _render_menu_query_count(self, num_pages):
        """Create ``num_pages`` pages and return the query count for get_nodes."""
        from djangocms_versioning.cms_menus import CMSMenu

        user = UserFactory()
        for _ in range(num_pages):
            PageContentWithVersionFactory(
                page=PageFactory(), language="en", version__created_by=user
            )

        request = type("Request", (), {
            "user": UserFactory(),
            "site": Site.objects.get_current(),
            "request_language": "en",
            "GET": {},
            "path": "/test/",
            "path_info": "/test/",
            "META": {"HTTP_HOST": "testserver"},
        })()
        menu = CMSMenu(request)

        with CaptureQueriesContext(connection) as ctx:
            menu.get_nodes(request)
        return len(ctx.captured_queries)

    def test_menu_rendering_does_not_scale_with_pages(self):
        """The number of queries must not grow with the number of pages.

        Version lookups in the node loop are prefetched, so rendering a larger
        page tree issues the same number of queries as a smaller one. A per-page
        version query (N+1) would make the larger count strictly greater.
        """
        if not conf.ENABLE_MENU_REGISTRATION:
            self.skipTest("Menu registration is not enabled")

        small = self._render_menu_query_count(2)
        # More pages accumulate in the same test DB; the menu now renders them all.
        large = self._render_menu_query_count(6)

        self.assertEqual(
            small,
            large,
            f"Menu query count scales with the number of pages ({small} -> {large}); "
            "suggests an N+1 in the version lookup (cms_menus.py).",
        )


class IndicatorPerformanceTestCase(PerformanceTestMixin, TestCase):
    """Test the version lookups behind the state indicators."""

    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.poll = PollFactory()
        self.poll_content = PollContentWithVersionFactory(
            poll=self.poll, language="en", version__created_by=self.user
        )

    def test_content_indicator_caches_result(self):
        """Repeated ``content_indicator`` calls query once and cache afterwards."""
        with self.assertNumQueries(1):
            for _ in range(3):
                content_indicator(self.poll_content)

    def test_content_indicator_uses_prefetched_versions(self):
        """Passing prefetched versions must avoid any database query."""
        poll_contents = []
        for _ in range(3):
            poll = PollFactory()
            poll_contents.append(
                PollContentWithVersionFactory(poll=poll, language="en", version__created_by=self.user)
            )

        prefetched = list(Version.objects.filter(
            object_id__in=[pc.pk for pc in poll_contents],
            content_type__model="pollcontent",
        ))
        for content in poll_contents:
            content._prefetched_versions = [v for v in prefetched if v.object_id == content.pk]

        with self.assertNumQueries(0):
            for content in poll_contents:
                content_indicator(content, versions=content._prefetched_versions)


class AdminPerformanceTestCase(PerformanceTestMixin, TestCase):
    """Test that the admin list display does not issue per-row queries."""

    def setUp(self):
        super().setUp()
        self.user = UserFactory(is_staff=True, is_superuser=True)
        self.num_objects = 10
        for _ in range(self.num_objects):
            poll = PollFactory()
            PollContentWithVersionFactory(poll=poll, language="en", version__created_by=self.user)

        model = PollContentWithVersionFactory._meta.model

        class TestAdmin(ExtendedVersionAdminMixin, django_admin.ModelAdmin):
            list_display = ["get_versioning_state", "get_author", "get_modified_date"]

        self.admin = TestAdmin(model, AdminSite())

    def test_admin_list_display_no_n_plus_1(self):
        """List display methods read prefetched versions (and authors), never the DB.

        ``get_queryset`` prefetches the versions together with their
        ``created_by`` author. Rendering the columns for every row must therefore
        add zero queries; a missing prefetch would add one query per row.
        """
        request = RequestFactory().get("/")
        request.user = self.user

        # Building the list is a small constant, independent of the row count.
        with self.assertMaxQueries(4):
            content_list = list(self.admin.get_queryset(request))
        self.assertEqual(len(content_list), self.num_objects)

        # Rendering every column for every row must not touch the database.
        with self.assertNumQueries(0):
            for obj in content_list:
                self.admin.get_versioning_state(obj)
                self.admin.get_author(obj)
                self.admin.get_modified_date(obj)


class ModelPerformanceTestCase(PerformanceTestMixin, TestCase):
    """Test that Version model operations stay query-efficient."""

    def setUp(self):
        super().setUp()
        self.user = UserFactory()

    def test_version_save_is_single_query(self):
        """Saving a version updates a single row without extra lookups."""
        poll = PollFactory()
        version = Version.objects.get_for_content(
            PollContentWithVersionFactory(poll=poll, language="en", version__created_by=self.user)
        )

        with self.assertNumQueries(1):
            version.save()

    def test_version_publish_no_n_plus_1(self):
        """Publishing unpublishes sibling versions without a per-sibling N+1.

        The grouper (poll) has a draft (en) and a published (fr) version; publishing
        the draft must unpublish the other in a bounded number of queries.
        """
        poll = PollFactory()
        draft = Version.objects.get_for_content(
            PollContentWithVersionFactory(
                poll=poll, language="en", version__created_by=self.user, version__state="draft"
            )
        )
        Version.objects.get_for_content(
            PollContentWithVersionFactory(
                poll=poll, language="fr", version__created_by=self.user, version__state="published"
            )
        )

        with self.assertMaxQueries(6):
            draft.publish(self.user)


# Run tests with: python -m pytest tests/test_performance.py -v
