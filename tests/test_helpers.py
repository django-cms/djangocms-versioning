from unittest import skipIf
from urllib.parse import parse_qs, urlparse

from cms import __version__ as cms_version
from cms.test_utils.testcases import CMSTestCase
from cms.toolbar.utils import get_object_edit_url
from django.http import QueryDict
from packaging.version import Version as PackageVersion

from djangocms_versioning import helpers
from djangocms_versioning.test_utils import factories
from djangocms_versioning.test_utils.polls.models import PollContent


class HelperUrlFunctionsTestCase(CMSTestCase):
    def test_get_editable_url_appends_params_for_editable_content(self):
        version = factories.PageVersionFactory(content__language="en")
        params = QueryDict("foo=bar&baz=qux")

        url = helpers.get_editable_url(version.content, params=params)

        parsed = urlparse(url)
        self.assertEqual(
            parsed.path, get_object_edit_url(version.content, language="en")
        )
        self.assertEqual(parse_qs(parsed.query), {"foo": ["bar"], "baz": ["qux"]})

    def test_get_editable_url_does_not_append_params_for_admin_change(self):
        poll_version = factories.PollVersionFactory()
        params = QueryDict("foo=bar&force_admin=1")

        url = helpers.get_editable_url(
            poll_version.content, force_admin=True, params=params
        )

        parsed = urlparse(url)
        self.assertEqual(
            parsed.path,
            helpers.get_admin_url(PollContent, "change", poll_version.content.pk),
        )
        self.assertEqual(parse_qs(parsed.query), {})

    @skipIf(
        PackageVersion(cms_version) < PackageVersion("5.1"),
        "get_object_live_url params supported only on django CMS 5.1+",
    )
    def test_get_object_live_url_appends_params(self):
        poll_version = factories.PollVersionFactory(content__language="en")
        params = QueryDict("foo=bar&baz=2")

        url = helpers.get_object_live_url(
            poll_version.content, language="en", params=params
        )

        parsed = urlparse(url)
        self.assertEqual(parsed.path, poll_version.content.get_absolute_url())
        self.assertEqual(parse_qs(parsed.query), {"foo": ["bar"], "baz": ["2"]})


class TestGetLatestAdminViewableContent(CMSTestCase):
    def setUp(self) -> None:
        """Creates a page, page content and a version object for the following tests"""
        self.page = factories.PageFactory()
        self.version = factories.PageVersionFactory(
            content__page=self.page,
            content__language="en",
        )

    def test_extra_grouping_fields_respects_language_with_prefetch(self):
        """Test that extra_grouping_fields (language) is respected when _prefetched_contents is present"""
        # Create content for two different languages
        en_version = self.version
        de_version = factories.PageVersionFactory(
            content__page=self.page,
            content__language="de",
        )

        # Get the actual PageContent objects from the versions

        en_content_obj = en_version.content
        de_content_obj = de_version.content

        # Simulate the admin prefetch pattern by manually setting up _prefetched_contents
        # with the versions prefetched
        en_content_obj._prefetched_versions = [en_version]
        de_content_obj._prefetched_versions = [de_version]

        # Set the _prefetched_contents on the page
        self.page._prefetched_contents = [de_content_obj, en_content_obj]  # order_by("-pk")

        # Now when calling get_latest_admin_viewable_content with language="en",
        # it should return only the English version, not the German version
        en_content = helpers.get_latest_admin_viewable_content(self.page, language="en")
        self.assertEqual(en_content.language, "en")
        self.assertEqual(en_content.versions.first(), en_version)

        # When calling with language="de", it should return the German version
        de_content = helpers.get_latest_admin_viewable_content(self.page, language="de")
        self.assertEqual(de_content.language, "de")
        self.assertEqual(de_content.versions.first(), de_version)

    def test_extra_grouping_fields_with_prefetch_published_only(self):
        """Test with prefetch when only published content exists (no draft)"""
        # Publish the English version (no draft exists)
        self.version.publish(user=self.get_superuser())

        # Create published German version
        de_version = factories.PageVersionFactory(
            content__page=self.page,
            content__language="de",
            state="published",
        )

        en_content_obj = self.version.content
        de_content_obj = de_version.content

        # Set up prefetched versions
        en_content_obj._prefetched_versions = [self.version]
        de_content_obj._prefetched_versions = [de_version]

        self.page._prefetched_contents = [de_content_obj, en_content_obj]

        # Should return published content when no draft exists
        en_content = helpers.get_latest_admin_viewable_content(self.page, language="en")
        self.assertEqual(en_content.language, "en")
        self.assertEqual(en_content.versions.first(), self.version)

        de_content = helpers.get_latest_admin_viewable_content(self.page, language="de")
        self.assertEqual(de_content.language, "de")
        self.assertEqual(de_content.versions.first(), de_version)

    def test_extra_grouping_fields_with_prefetch_archived_only(self):
        """Test with prefetch when only archived content exists (no draft or published)"""
        # Archive the English version
        self.version.archive(user=self.get_superuser())

        # Create archived German version
        de_version = factories.PageVersionFactory(
            content__page=self.page,
            content__language="de",
            state="archived",
        )

        en_content_obj = self.version.content
        de_content_obj = de_version.content

        # Set up prefetched versions
        en_content_obj._prefetched_versions = [self.version]
        de_content_obj._prefetched_versions = [de_version]

        self.page._prefetched_contents = [de_content_obj, en_content_obj]

        # Without include_unpublished_archived, should return None
        en_content = helpers.get_latest_admin_viewable_content(self.page, language="en")
        self.assertIsNone(en_content)

        # With include_unpublished_archived, should return archived content
        en_content = helpers.get_latest_admin_viewable_content(
            self.page, language="en", include_unpublished_archived=True
        )
        self.assertEqual(en_content.language, "en")
        self.assertEqual(en_content.versions.first(), self.version)

    def test_extra_grouping_fields_respects_language_without_prefetch(self):
        """Test that extra_grouping_fields (language) is respected when _prefetched_contents is not present"""
        # Create content for two different languages
        en_version = self.version
        de_version = factories.PageVersionFactory(
            content__page=self.page,
            content__language="de",
        )

        # Ensure _prefetched_contents is not present
        if hasattr(self.page, "_prefetched_contents"):
            delattr(self.page, "_prefetched_contents")

        # When calling get_latest_admin_viewable_content with language="en",
        # it should return only the English version
        en_content = helpers.get_latest_admin_viewable_content(self.page, language="en")
        self.assertEqual(en_content.language, "en")
        self.assertEqual(en_content.versions.first(), en_version)

        # When calling with language="de", it should return the German version
        de_content = helpers.get_latest_admin_viewable_content(self.page, language="de")
        self.assertEqual(de_content.language, "de")
        self.assertEqual(de_content.versions.first(), de_version)

    def test_extra_grouping_fields_without_prefetch_published_only(self):
        """Test without prefetch when only published content exists (no draft)"""
        # Publish the English version (no draft exists)
        self.version.publish(user=self.get_superuser())

        # Create published German version
        de_version = factories.PageVersionFactory(
            content__page=self.page,
            content__language="de",
            state="published",
        )

        # Ensure _prefetched_contents is not present
        if hasattr(self.page, "_prefetched_contents"):
            delattr(self.page, "_prefetched_contents")

        # Should return published content when no draft exists
        en_content = helpers.get_latest_admin_viewable_content(self.page, language="en")
        self.assertEqual(en_content.language, "en")
        self.assertEqual(en_content.versions.first(), self.version)

        de_content = helpers.get_latest_admin_viewable_content(self.page, language="de")
        self.assertEqual(de_content.language, "de")
        self.assertEqual(de_content.versions.first(), de_version)

    def test_extra_grouping_fields_without_prefetch_archived_only(self):
        """Test without prefetch when only archived content exists (no draft or published)"""
        # Archive the English version
        self.version.archive(user=self.get_superuser())

        # Create archived German version
        factories.PageVersionFactory(
            content__page=self.page,
            content__language="de",
            state="archived",
        )

        # Ensure _prefetched_contents is not present
        if hasattr(self.page, "_prefetched_contents"):
            delattr(self.page, "_prefetched_contents")

        # Without include_unpublished_archived, should return None
        en_content = helpers.get_latest_admin_viewable_content(self.page, language="en")
        self.assertIsNone(en_content)

        # With include_unpublished_archived, should return archived content
        en_content = helpers.get_latest_admin_viewable_content(
            self.page, language="en", include_unpublished_archived=True
        )
        self.assertEqual(en_content.language, "en")
        self.assertEqual(en_content.versions.first(), self.version)
