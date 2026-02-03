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
