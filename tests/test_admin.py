import datetime
import warnings
from collections import OrderedDict
from distutils.version import LooseVersion
from unittest import skip, skipIf
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

import django
from django.apps import apps
from django.contrib import admin, messages
from django.contrib.admin.utils import flatten_fieldsets
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory
from django.test.utils import ignore_warnings
from django.urls import reverse
from django.utils.timezone import now, utc

from cms.test_utils.testcases import CMSTestCase
from cms.toolbar.utils import get_object_edit_url, get_object_preview_url
from cms.utils.conf import get_cms_setting
from cms.utils.helpers import is_editable_model
from cms.utils.urlutils import admin_reverse

import pytz
from bs4 import BeautifulSoup
from freezegun import freeze_time

import djangocms_versioning.helpers
from djangocms_versioning import constants, helpers
from djangocms_versioning.admin import (
    VersionAdmin,
    VersionChangeList,
    VersioningAdminMixin,
)
from djangocms_versioning.cms_config import VersioningCMSConfig
from djangocms_versioning.helpers import (
    register_versionadmin_proxy,
    replace_admin_for_models,
    versioning_admin_factory,
)
from djangocms_versioning.models import StateTracking, Version
from djangocms_versioning.test_utils import factories
from djangocms_versioning.test_utils.blogpost.cms_config import BlogpostCMSConfig
from djangocms_versioning.test_utils.blogpost.models import BlogContent
from djangocms_versioning.test_utils.polls.cms_config import PollsCMSConfig
from djangocms_versioning.test_utils.polls.models import Answer, Poll, PollContent


DJANGO_GTE_21 = LooseVersion(django.__version__) >= LooseVersion("2.1")


class BaseStateTestCase(CMSTestCase):
    def assertRedirectsToVersionList(self, response, version):
        parsed = urlparse(response.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            parsed.path,
            self.get_admin_url(version.versionable.version_model_proxy, "changelist"),
        )
        self.assertEqual(
            {k: v[0] for k, v in parse_qs(parsed.query).items()},
            {
                "poll": str(version.content.poll.pk),
                "language": version.content.language,
            },
        )


class AdminVersioningTestCase(CMSTestCase):
    def test_admin_factory(self):
        """Test that `versioning_admin_factory` creates a class based on
        provided admin class
        """
        admin_class = type("TestAdmin", (admin.ModelAdmin,), {})
        mixin = type("Mixin", (), {})

        new_admin_class = versioning_admin_factory(admin_class, mixin)
        mro = new_admin_class.mro()

        # both base classes are used
        self.assertTrue(issubclass(new_admin_class, admin_class))
        self.assertTrue(issubclass(new_admin_class, mixin))

        # mixin takes precedence over user-defined class
        self.assertTrue(mro.index(mixin) < mro.index(admin_class))


class AdminReplaceVersioningTestCase(CMSTestCase):
    def setUp(self):
        self.model = Poll
        self.site = admin.AdminSite()
        self.admin_class = type("TestAdmin", (admin.ModelAdmin,), {})

    def test_replace_admin_on_unregistered_model(self):
        """Test that calling `replace_admin_for_models` with a model that
        isn't registered in admin is a no-op.
        """
        mixin = type("Mixin", (), {})
        replace_admin_for_models([(self.model, mixin)], self.site)

        self.assertNotIn(self.model, self.site._registry)

    def test_replace_admin_on_registered_models_default_site(self):
        mixin = type("Mixin", (), {})

        with patch.object(
            djangocms_versioning.helpers, "_replace_admin_for_model"
        ) as mock:
            replace_admin_for_models([(PollContent, mixin)])

        mock.assert_called_with(admin.site._registry[PollContent], mixin, admin.site)

    def test_replace_admin_on_registered_models(self):
        self.site.register(self.model, self.admin_class)
        self.site.register(Answer, self.admin_class)
        models = [self.model, Answer]

        replace_admin_for_models(
            [(model, VersioningAdminMixin) for model in models], self.site
        )

        for model in models:
            self.assertIn(model, self.site._registry)
            self.assertIn(self.admin_class, self.site._registry[model].__class__.mro())
            self.assertIn(
                VersioningAdminMixin, self.site._registry[model].__class__.mro()
            )

    def test_replace_default_admin_on_registered_model(self):
        """Test that registering a model without specifying own
        ModelAdmin class still results in overridden admin class.
        """
        self.site.register(self.model)

        replace_admin_for_models([(self.model, VersioningAdminMixin)], self.site)

        self.assertIn(self.model, self.site._registry)
        self.assertIn(
            VersioningAdminMixin, self.site._registry[self.model].__class__.mro()
        )

    def test_replace_admin_again(self):
        """Test that, if a model's admin class already subclasses
        VersioningAdminMixin, nothing happens.
        """
        version_admin = versioning_admin_factory(self.admin_class, VersioningAdminMixin)
        self.site.register(self.model, version_admin)

        replace_admin_for_models([(self.model, VersioningAdminMixin)], self.site)

        self.assertIn(self.model, self.site._registry)
        self.assertEqual(self.site._registry[self.model].__class__, version_admin)


class AdminAddVersionTestCase(CMSTestCase):
    def _get_admin_class_obj(self, content_model):
        """Helper method to set up a model admin class that derives
        from VersioningAdminMixin
        """
        admin_class = type(
            "VersioningModelAdmin", (VersioningAdminMixin, admin.ModelAdmin), {}
        )
        admin_site = admin.AdminSite()
        return admin_class(model=content_model, admin_site=admin_site)

    def test_poll_version_is_added_for_change_false(self):
        model_admin = self._get_admin_class_obj(PollContent)
        with freeze_time("2011-01-06"):
            pc1 = factories.PollContentFactory.build(poll=factories.PollFactory())
            request = RequestFactory().get("/admin/polls/pollcontent/")
            request.user = factories.UserFactory()
            model_admin.save_model(request, pc1, form=None, change=False)
            check_obj = Version.objects.get(
                content_type=ContentType.objects.get_for_model(pc1), object_id=pc1.pk
            )
            self.assertTrue(check_obj)
            self.assertEqual(
                check_obj.created, datetime.datetime(2011, 1, 6, tzinfo=pytz.utc)
            )

    def test_poll_version_is_not_added_for_change_true(self):
        model_admin = self._get_admin_class_obj(PollContent)
        pc2 = factories.PollContentFactory()
        request = RequestFactory().get("/admin/polls/pollcontent/")
        model_admin.save_model(request, pc2, form=None, change=True)
        check_obj_exist = Version.objects.filter(
            content_type=ContentType.objects.get_for_model(pc2), object_id=pc2.pk
        ).exists()
        self.assertFalse(check_obj_exist)

    def test_blogpost_version_is_added_for_change_false(self):
        model_admin = self._get_admin_class_obj(BlogContent)
        bc1 = factories.BlogContentFactory.build(blogpost=factories.BlogPostFactory())
        request = RequestFactory().get("/admin/blogposts/blogcontent/")
        request.user = factories.UserFactory()
        model_admin.save_model(request, bc1, form=None, change=False)
        check_obj_exist = Version.objects.filter(
            content_type=ContentType.objects.get_for_model(bc1), object_id=bc1.pk
        ).exists()
        self.assertTrue(check_obj_exist)

    def test_blogpost_version_is_not_added_for_change_true(self):
        model_admin = self._get_admin_class_obj(BlogContent)
        bc2 = factories.BlogContentFactory()
        request = RequestFactory().get("/admin/blogposts/blogcontent/")
        model_admin.save_model(request, bc2, form=None, change=True)
        check_obj_exist = Version.objects.filter(
            content_type=ContentType.objects.get_for_model(bc2), object_id=bc2.pk
        ).exists()
        self.assertFalse(check_obj_exist)


class ContentAdminChangelistTestCase(CMSTestCase):
    def _get_admin_class_obj(self, content_model):
        """Helper method to set up a model admin class that derives
        from VersioningAdminMixin
        """
        admin_class = type(
            "VersioningModelAdmin", (VersioningAdminMixin, admin.ModelAdmin), {}
        )
        admin_site = admin.AdminSite()
        return admin_class(model=content_model, admin_site=admin_site)

    def test_only_fetches_latest_content_records(self):
        """Returns content records of the latest content
        """
        poll1 = factories.PollFactory()
        poll2 = factories.PollFactory()
        # Make sure django sets the created date far in the past
        with freeze_time("2014-01-01"):
            factories.PollContentWithVersionFactory.create_batch(2, poll=poll1)
            factories.PollContentWithVersionFactory(poll=poll2)
        # For these the created date will be now
        poll_content1 = factories.PollContentWithVersionFactory(poll=poll1)
        poll_content2 = factories.PollContentWithVersionFactory(poll=poll2)
        poll_content3 = factories.PollContentWithVersionFactory()

        with self.login_user_context(self.get_superuser()):
            response = self.client.get(self.get_admin_url(PollContent, "changelist"))

        self.assertQuerysetEqual(
            response.context["cl"].queryset,
            [poll_content1.pk, poll_content2.pk, poll_content3.pk],
            transform=lambda x: x.pk,
            ordered=False,
        )

    def test_records_filtering_is_generic(self):
        """Check there's nothing specific to polls hardcoded in
        VersioningChangeListMixin.get_queryset. This repeats a similar test
        for PollContent, but using BlogContent instead.
        """
        post = factories.BlogPostFactory()
        # Make sure django sets the created date far in the past
        with freeze_time("2016-06-06"):
            factories.BlogContentWithVersionFactory(blogpost=post)
        # For these the created date will be now
        blog_content1 = factories.BlogContentWithVersionFactory(blogpost=post)
        blog_content2 = factories.BlogContentWithVersionFactory()

        with self.login_user_context(self.get_superuser()):
            response = self.client.get(self.get_admin_url(BlogContent, "changelist"))

        self.assertQuerysetEqual(
            response.context["cl"].queryset,
            [blog_content1.pk, blog_content2.pk],
            transform=lambda x: x.pk,
            ordered=False,
        )


class AdminRegisterVersionTestCase(CMSTestCase):
    def test_register_version_admin(self):
        """Test that a model admin based on VersionAdmin class is registered
        for specified VersionableItem
        """
        site = admin.AdminSite()

        versionable = Mock(spec=[], version_model_proxy=Version, grouper_model=Poll)
        register_versionadmin_proxy(versionable, site)

        self.assertIn(Version, site._registry)
        self.assertIn(VersionAdmin, site._registry[Version].__class__.mro())

    @ignore_warnings(module="djangocms_versioning.helpers")
    def test_register_version_admin_again(self):
        """Test that attempting to register a proxy model again
        doesn't do anything.
        """
        existing_admin = type("TestAdmin", (admin.ModelAdmin,), {})
        site = admin.AdminSite()
        site.register(Version, existing_admin)
        versionable = Mock(spec=[], version_model_proxy=Version, grouper_model=Poll)

        with patch.object(site, "register") as mock:
            register_versionadmin_proxy(versionable, site)

        mock.assert_not_called()

    def test_register_versionadmin_proxy_warning(self):
        existing_admin = type("TestAdmin", (admin.ModelAdmin,), {})
        site = admin.AdminSite()
        site.register(Version, existing_admin)
        versionable = Mock(spec=[], version_model_proxy=Version, grouper_model=Poll)

        with patch.object(warnings, "warn") as mock:
            register_versionadmin_proxy(versionable, site)
        message = "{!r} is already registered with admin.".format(Version)
        mock.assert_called_with(message, UserWarning)


class VersionAdminTestCase(CMSTestCase):
    def setUp(self):
        self.site = admin.AdminSite()
        self.site.register(Version, VersionAdmin)

    def test_get_changelist(self):
        self.assertEqual(
            self.site._registry[Version].get_changelist(
                RequestFactory().get("/admin/")
            ),
            VersionChangeList,
        )

    @skip("Prefetching is disabled")
    def test_queryset_content_prefetching(self):
        factories.PollVersionFactory.create_batch(4)
        with self.assertNumQueries(2):
            qs = self.site._registry[Version].get_queryset(RequestFactory().get("/"))
            for version in qs:
                version.content
        self.assertTrue(qs._prefetch_done)
        self.assertIn("content", qs._prefetch_related_lookups)

    def test_content_link_editable_object(self):
        """
        The link returned is the change url for an editable object
        """
        version = factories.PageVersionFactory(content__title="mypage")
        preview_url = admin_reverse(
            "cms_placeholder_render_object_preview",
            args=(version.content_type_id, version.object_id),
        )
        self.assertEqual(
            self.site._registry[Version].content_link(version),
            '<a target="_top" class="js-versioning-close-sideframe" href="{url}">{label}</a>'.format(
                url=preview_url, label=version.content
            ),
        )

    def test_content_link_non_editable_object_with_preview_url(self):
        """
        The link returned is the preview url for a non editable object with preview url config in versionable
        """
        version = factories.PollVersionFactory(content__text="test4")
        self.assertEqual(
            self.site._registry[Version].content_link(version),
            '<a target="_top" class="js-versioning-close-sideframe" href="{url}">{label}</a>'.format(
                url="/en/admin/polls/pollcontent/1/preview/", label="test4"
            ),
        )

    def test_content_link_for_non_editable_object_with_no_preview_url(self):
        """
        The link returned is the change url for a non editable object
        """
        version = factories.BlogPostVersionFactory(content__text="test4")
        self.assertFalse(is_editable_model(version))
        self.assertEqual(
            self.site._registry[Version].content_link(version),
            '<a target="_top" class="js-versioning-close-sideframe" href="{url}">{label}</a>'.format(
                url="/en/admin/blogpost/blogcontent/1/change/", label="test4"
            ),
        )

    def test_content_link_for_editable_object_with_no_preview_url(self):
        """
        The link returned is the object preview url for a editable object
        """
        version = factories.PageVersionFactory(content__title="test5")
        with patch.object(helpers, "is_editable_model", return_value=True):
            self.assertEqual(
                self.site._registry[Version].content_link(version),
                '<a target="_top" class="js-versioning-close-sideframe" href="{url}">{label}</a>'.format(
                    url=get_object_preview_url(version.content), label=version.content
                ),
            )


class VersionAdminActionsTestCase(CMSTestCase):
    def setUp(self):
        self.versionable = PollsCMSConfig.versioning[0]
        self.version_admin = admin.site._registry[self.versionable.version_model_proxy]

    def test_edit_action_link_enabled_state(self):
        """
        The edit action is active
        """
        version = factories.PollVersionFactory(state=constants.DRAFT)
        user = factories.UserFactory()
        request = RequestFactory().get("/admin/polls/pollcontent/")
        request.user = user
        draft_edit_url = self.get_admin_url(
            self.versionable.version_model_proxy, "edit_redirect", version.pk
        )

        actual_enabled_control = self.version_admin._get_edit_link(
            version, request, disabled=False
        )
        expected_enabled_state = (
            '<a class="btn cms-versioning-action-btn js-versioning-action"'
            ' href="%s" title="Edit">'
        ) % draft_edit_url

        self.assertIn(expected_enabled_state, actual_enabled_control)

    def test_edit_action_link_disabled_state(self):
        """
        The edit action is disabled
        """
        version = factories.PollVersionFactory(state=constants.DRAFT)
        user = factories.UserFactory()
        request = RequestFactory().get("/admin/polls/pollcontent/")
        request.user = user

        actual_disabled_control = self.version_admin._get_edit_link(
            version, request, disabled=True
        )
        expected_disabled_control = (
            '<a class="btn cms-versioning-action-btn inactive" title="Edit">'
        )

        self.assertIn(expected_disabled_control, actual_disabled_control)

    def test_revert_action_link_enable_state(self):
        """
        The edit action is active
        """
        version = factories.PollVersionFactory(state=constants.ARCHIVED)
        user = factories.UserFactory()
        request = RequestFactory().get("/admin/polls/pollcontent/")
        version.created_by = request.user = user
        actual_enabled_control = self.version_admin._get_revert_link(version, request)
        draft_revert_url = self.get_admin_url(
            self.versionable.version_model_proxy, "revert", version.pk
        )
        expected_enabled_state = (
            '<a class="btn cms-form-get-method cms-versioning-action-btn js-versioning-action '
            'js-versioning-keep-sideframe" '
            'href="%s" '
            'title="Revert">'
        ) % draft_revert_url
        self.assertIn(expected_enabled_state, actual_enabled_control.replace("\n", ""))

    def test_revert_action_link_for_draft_state(self):
        """
        The revert url should be null for draft state
        """
        version = factories.PollVersionFactory(state=constants.DRAFT)
        request = RequestFactory().get("/admin/polls/pollcontent/")
        actual_disabled_control = self.version_admin._get_revert_link(version, request)
        expected_disabled_control = ""
        self.assertIn(
            expected_disabled_control, actual_disabled_control.replace("\n", "")
        )

    def test_revert_action_link_for_published_state(self):
        """
        The revert url should be null for unpublished state
        """
        version = factories.PollVersionFactory(state=constants.PUBLISHED)
        request = RequestFactory().get("/admin/polls/pollcontent/")
        actual_disabled_control = self.version_admin._get_revert_link(version, request)
        expected_disabled_control = ""
        self.assertIn(
            expected_disabled_control, actual_disabled_control.replace("\n", "")
        )

    def test_discard_action_link_enabled_state(self):
        """
        The edit action is active
        """
        version = factories.PollVersionFactory(state=constants.DRAFT)
        request = RequestFactory().get("/admin/polls/pollcontent/")
        request.user = factories.UserFactory()
        draft_discard_url = self.get_admin_url(
            self.versionable.version_model_proxy, "discard", version.pk
        )

        actual_enabled_control = self.version_admin._get_discard_link(version, request)

        expected_enabled_state = (
            '<a class="btn cms-form-get-method cms-versioning-action-btn js-versioning-action '
            'js-versioning-keep-sideframe" '
            'href="%s" '
            'title="Discard">'
        ) % draft_discard_url
        self.assertIn(expected_enabled_state, actual_enabled_control.replace("\n", ""))

    def test_discard_action_link_for_archive_state(self):
        """
        The revert url should be null for archive state
        """
        version = factories.PollVersionFactory(state=constants.ARCHIVED)
        request = RequestFactory().get("/admin/polls/pollcontent/")
        request.user = factories.UserFactory()
        actual_disabled_control = self.version_admin._get_discard_link(version, request)
        expected_disabled_control = ""
        self.assertIn(
            expected_disabled_control, actual_disabled_control.replace("\n", "")
        )

    def test_discard_action_link_for_unpublished_state(self):
        """
        The revert url should be null for unpublished state
        """
        version = factories.PollVersionFactory(state=constants.UNPUBLISHED)
        request = RequestFactory().get("/admin/polls/pollcontent/")
        request.user = factories.UserFactory()
        actual_disabled_control = self.version_admin._get_discard_link(version, request)
        expected_disabled_control = ""
        self.assertIn(
            expected_disabled_control, actual_disabled_control.replace("\n", "")
        )

    def test_discard_action_link_for_published_state(self):
        """
        The revert url should be null for unpublished state
        """
        version = factories.PollVersionFactory(state=constants.PUBLISHED)
        request = RequestFactory().get("/admin/polls/pollcontent/")
        request.user = factories.UserFactory()
        actual_disabled_control = self.version_admin._get_discard_link(version, request)
        expected_disabled_control = ""
        self.assertIn(
            expected_disabled_control, actual_disabled_control.replace("\n", "")
        )

    def test_revert_action_link_for_archive_state(self):
        """
        The revert url should be null for unpublished state
        """
        version = factories.PollVersionFactory(state=constants.UNPUBLISHED)
        user = factories.UserFactory()
        archive_version = version.copy(user)
        archive_version.archive(user)
        request = RequestFactory().get("/admin/polls/pollcontent/")
        request.user = user
        actual_disabled_control = self.version_admin._get_revert_link(
            archive_version, request
        )
        draft_revert_url = self.get_admin_url(
            self.versionable.version_model_proxy, "revert", archive_version.pk
        )
        expected_disabled_control = (
            '<a class="btn cms-form-get-method cms-versioning-action-btn js-versioning-action '
            'js-versioning-keep-sideframe" '
            'href="%s" '
            'title="Revert">'
        ) % draft_revert_url

        self.assertIn(
            expected_disabled_control, actual_disabled_control.replace("\n", "")
        )


class StateActionsTestCase(CMSTestCase):
    def test_archive_in_state_actions_for_draft_version(self):
        version = factories.PollVersionFactory(state=constants.DRAFT)
        request = RequestFactory().get("/admin/polls/pollcontent/")
        request.user = factories.UserFactory()
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == "PollContentVersion"
        ][0]
        archive_url = reverse(
            "admin:djangocms_versioning_pollcontentversion_archive", args=(version.pk,)
        )

        state_actions = admin.site._registry[version_model_proxy]._state_actions(
            request
        )(version)

        self.assertIn(archive_url, state_actions)

    def test_archive_not_in_state_actions_for_archived_version(self):
        version = factories.PollVersionFactory(state=constants.ARCHIVED)
        request = RequestFactory().get("/admin/polls/pollcontent/")
        request.user = factories.UserFactory()
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == "PollContentVersion"
        ][0]
        archive_url = reverse(
            "admin:djangocms_versioning_pollcontentversion_archive", args=(version.pk,)
        )

        state_actions = admin.site._registry[version_model_proxy]._state_actions(
            request
        )(version)

        self.assertNotIn(archive_url, state_actions)

    def test_archive_not_in_state_actions_for_published_version(self):
        version = factories.PollVersionFactory(state=constants.PUBLISHED)
        request = RequestFactory().get("/admin/polls/pollcontent/")
        request.user = factories.UserFactory()
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == "PollContentVersion"
        ][0]
        archive_url = reverse(
            "admin:djangocms_versioning_pollcontentversion_archive", args=(version.pk,)
        )

        state_actions = admin.site._registry[version_model_proxy]._state_actions(
            request
        )(version)

        self.assertNotIn(archive_url, state_actions)

    def test_archive_not_in_state_actions_for_unpublished_version(self):
        version = factories.PollVersionFactory(state=constants.UNPUBLISHED)
        request = RequestFactory().get("/admin/polls/pollcontent/")
        request.user = factories.UserFactory()
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == "PollContentVersion"
        ][0]
        archive_url = reverse(
            "admin:djangocms_versioning_pollcontentversion_archive", args=(version.pk,)
        )

        state_actions = admin.site._registry[version_model_proxy]._state_actions(
            request
        )(version)

        self.assertNotIn(archive_url, state_actions)

    def test_publish_in_state_actions_for_draft_version(self):
        version = factories.PollVersionFactory(state=constants.DRAFT)
        request = RequestFactory().get("/admin/polls/pollcontent/")
        request.user = factories.UserFactory()
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == "PollContentVersion"
        ][0]
        publish_url = reverse(
            "admin:djangocms_versioning_pollcontentversion_publish", args=(version.pk,)
        )

        state_actions = admin.site._registry[version_model_proxy]._state_actions(
            request
        )(version)

        self.assertIn(publish_url, state_actions)

    def test_publish_not_in_state_actions_for_archived_version(self):
        version = factories.PollVersionFactory(state=constants.ARCHIVED)
        request = RequestFactory().get("/admin/polls/pollcontent/")
        request.user = factories.UserFactory()
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == "PollContentVersion"
        ][0]
        publish_url = reverse(
            "admin:djangocms_versioning_pollcontentversion_publish", args=(version.pk,)
        )

        state_actions = admin.site._registry[version_model_proxy]._state_actions(
            request
        )(version)

        self.assertNotIn(publish_url, state_actions)

    def test_publish_not_in_state_actions_for_published_version(self):
        version = factories.PollVersionFactory(state=constants.PUBLISHED)
        request = RequestFactory().get("/admin/polls/pollcontent/")
        request.user = factories.UserFactory()
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == "PollContentVersion"
        ][0]
        publish_url = reverse(
            "admin:djangocms_versioning_pollcontentversion_publish", args=(version.pk,)
        )

        state_actions = admin.site._registry[version_model_proxy]._state_actions(
            request
        )(version)

        self.assertNotIn(publish_url, state_actions)

    def test_publish_not_in_state_actions_for_unpublished_version(self):
        version = factories.PollVersionFactory(state=constants.UNPUBLISHED)
        request = RequestFactory().get("/admin/polls/pollcontent/")
        request.user = factories.UserFactory()
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == "PollContentVersion"
        ][0]
        publish_url = reverse(
            "admin:djangocms_versioning_pollcontentversion_publish", args=(version.pk,)
        )

        state_actions = admin.site._registry[version_model_proxy]._state_actions(
            request
        )(version)

        self.assertNotIn(publish_url, state_actions)

    def test_unpublish_in_state_actions_for_published_version(self):
        version = factories.PollVersionFactory(state=constants.PUBLISHED)
        request = RequestFactory().get("/admin/polls/pollcontent/")
        request.user = factories.UserFactory()
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == "PollContentVersion"
        ][0]
        unpublish_url = reverse(
            "admin:djangocms_versioning_pollcontentversion_unpublish",
            args=(version.pk,),
        )

        state_actions = admin.site._registry[version_model_proxy]._state_actions(
            request
        )(version)

        self.assertIn(unpublish_url, state_actions)

    def test_unpublish_not_in_state_actions_for_archived_version(self):
        version = factories.PollVersionFactory(state=constants.ARCHIVED)
        request = RequestFactory().get("/admin/polls/pollcontent/")
        request.user = factories.UserFactory()
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == "PollContentVersion"
        ][0]
        unpublish_url = reverse(
            "admin:djangocms_versioning_pollcontentversion_unpublish",
            args=(version.pk,),
        )

        state_actions = admin.site._registry[version_model_proxy]._state_actions(
            request
        )(version)

        self.assertNotIn(unpublish_url, state_actions)

    def test_unpublish_not_in_state_actions_for_unpublished_version(self):
        version = factories.PollVersionFactory(state=constants.UNPUBLISHED)
        request = RequestFactory().get("/admin/polls/pollcontent/")
        request.user = factories.UserFactory()
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == "PollContentVersion"
        ][0]
        unpublish_url = reverse(
            "admin:djangocms_versioning_pollcontentversion_unpublish",
            args=(version.pk,),
        )

        state_actions = admin.site._registry[version_model_proxy]._state_actions(
            request
        )(version)

        self.assertNotIn(unpublish_url, state_actions)

    def test_unpublish_not_in_state_actions_for_draft_version(self):
        version = factories.PollVersionFactory(state=constants.DRAFT)
        request = RequestFactory().get("/admin/polls/pollcontent/")
        request.user = factories.UserFactory()
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == "PollContentVersion"
        ][0]
        unpublish_url = reverse(
            "admin:djangocms_versioning_pollcontentversion_unpublish",
            args=(version.pk,),
        )

        state_actions = admin.site._registry[version_model_proxy]._state_actions(
            request
        )(version)

        self.assertNotIn(unpublish_url, state_actions)

    def test_edit_in_state_actions_for_draft_version(self):
        version = factories.PollVersionFactory(state=constants.DRAFT)
        request = RequestFactory().get("/admin/polls/pollcontent/")
        request.user = factories.UserFactory()
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == "PollContentVersion"
        ][0]
        edit_url = reverse(
            "admin:djangocms_versioning_pollcontentversion_edit_redirect",
            args=(version.pk,),
        )

        state_actions = admin.site._registry[version_model_proxy]._state_actions(
            request
        )(version)

        self.assertIn(edit_url, state_actions)

    def test_edit_not_in_state_actions_for_archived_version(self):
        version = factories.PollVersionFactory(state=constants.ARCHIVED)
        request = RequestFactory().get("/admin/polls/pollcontent/")
        request.user = factories.UserFactory()
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == "PollContentVersion"
        ][0]
        edit_url = reverse(
            "admin:djangocms_versioning_pollcontentversion_edit_redirect",
            args=(version.pk,),
        )

        state_actions = admin.site._registry[version_model_proxy]._state_actions(
            request
        )(version)

        self.assertNotIn(edit_url, state_actions)

    def test_edit_in_state_actions_for_published_version(self):
        version = factories.PollVersionFactory(state=constants.PUBLISHED)
        request = RequestFactory().get("/admin/polls/pollcontent/")
        request.user = factories.UserFactory()
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == "PollContentVersion"
        ][0]
        edit_url = reverse(
            "admin:djangocms_versioning_pollcontentversion_edit_redirect",
            args=(version.pk,),
        )

        state_actions = admin.site._registry[version_model_proxy]._state_actions(
            request
        )(version)

        self.assertIn(edit_url, state_actions)

    def test_edit_not_in_state_actions_for_published_version_when_draft_exists(self):
        version = factories.PollVersionFactory(
            state=constants.PUBLISHED, content__language="en"
        )
        request = RequestFactory().get("/admin/polls/pollcontent/")
        request.user = factories.UserFactory()
        factories.PollVersionFactory(
            state=constants.DRAFT,
            content__poll=version.content.poll,
            content__language="en",
        )
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == "PollContentVersion"
        ][0]
        edit_url = reverse(
            "admin:djangocms_versioning_pollcontentversion_edit_redirect",
            args=(version.pk,),
        )

        state_actions = admin.site._registry[version_model_proxy]._state_actions(
            request
        )(version)

        self.assertNotIn(edit_url, state_actions)

    def test_edit_not_in_state_actions_for_unpublished_version(self):
        version = factories.PollVersionFactory(state=constants.UNPUBLISHED)
        request = RequestFactory().get("/admin/polls/pollcontent/")
        request.user = factories.UserFactory()
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == "PollContentVersion"
        ][0]
        edit_url = reverse(
            "admin:djangocms_versioning_pollcontentversion_edit_redirect",
            args=(version.pk,),
        )

        state_actions = admin.site._registry[version_model_proxy]._state_actions(
            request
        )(version)

        self.assertNotIn(edit_url, state_actions)


class VersionAdminViewTestCase(CMSTestCase):
    def setUp(self):
        self.superuser = self.get_superuser()
        self.versionable = PollsCMSConfig.versioning[0]

    def test_version_adding_is_disabled(self):
        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.get_admin_url(self.versionable.version_model_proxy, "add")
            )
        self.assertEqual(response.status_code, 403)

    @skipIf(DJANGO_GTE_21, "Django>=2.1")
    def test_version_editing_is_disabled(self):
        version = factories.PollVersionFactory(content__text="test5")
        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.get_admin_url(
                    self.versionable.version_model_proxy, "change", version.pk
                )
            )
        self.assertEqual(response.status_code, 403)

    @skipIf(not DJANGO_GTE_21, "Django<2.1")
    def test_version_editing_readonly_fields(self):
        version = factories.PollVersionFactory(content__text="test5")
        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.get_admin_url(
                    self.versionable.version_model_proxy, "change", version.pk
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["adminform"].fieldsets[0][1]["fields"],
            response.context["adminform"].readonly_fields,
        )

    def test_version_deleting_is_disabled(self):
        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.get_admin_url(self.versionable.version_model_proxy, "delete", 1)
            )
        self.assertEqual(response.status_code, 403)


class GrouperFormViewTestCase(CMSTestCase):
    def setUp(self):
        self.versionable = PollsCMSConfig.versioning[0]

    def test_grouper_view_requires_staff_permissions(self):
        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.get(
                self.get_admin_url(self.versionable.version_model_proxy, "grouper")
            )
        self.assertEqual(response.status_code, 200)

    def test_grouper_view_requires_staff_permissions_(self):
        url = self.get_admin_url(self.versionable.version_model_proxy, "grouper")
        with self.login_user_context(self.get_standard_user()):
            response = self.client.get(url)

        self.assertRedirects(response, admin_reverse("login") + "?next=" + url)


class ArchiveViewTestCase(BaseStateTestCase):
    def setUp(self):
        self.versionable = PollsCMSConfig.versioning[0]

    def test_archive_view_sets_modified_time(self):
        poll_version = factories.PollVersionFactory(state=constants.DRAFT)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "archive", poll_version.pk
        )
        user = self.get_staff_user_with_no_permissions()
        with freeze_time("2999-01-11 00:00:00", tz_offset=0), self.login_user_context(
            user
        ):
            self.client.post(url)

        # Refresh object after update
        poll_version.refresh_from_db(fields=["modified"])
        # check modified time is updated as freeze time
        self.assertEqual(
            poll_version.modified,
            datetime.datetime(2999, 1, 11, 00, 00, 00, tzinfo=utc),
        )

    def test_archive_view_doesnt_allow_user_without_staff_permissions(self):
        poll_version = factories.PollVersionFactory(state=constants.DRAFT)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "archive", poll_version.pk
        )
        with self.login_user_context(self.get_standard_user()):
            response = self.client.post(url)

        self.assertRedirects(response, admin_reverse("login") + "?next=" + url)
        # status hasn't changed
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.DRAFT)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    @freeze_time(None)
    @patch("django.contrib.admin.ModelAdmin.message_user")
    def test_archive_view_sets_state_and_redirects(self, mocked_messages):
        poll_version = factories.PollVersionFactory(state=constants.DRAFT)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "archive", poll_version.pk
        )
        user = self.get_staff_user_with_no_permissions()

        with self.login_user_context(user):
            response = self.client.post(url)

        # State updated
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.ARCHIVED)
        # State change tracked
        tracking = StateTracking.objects.get()
        self.assertEqual(tracking.version, poll_version_)
        self.assertEqual(tracking.date, now())
        self.assertEqual(tracking.old_state, constants.DRAFT)
        self.assertEqual(tracking.new_state, constants.ARCHIVED)
        self.assertEqual(tracking.user, user)
        # Message displayed
        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], "Version archived")
        # Redirect happened
        self.assertRedirectsToVersionList(response, poll_version)

    @patch("django.contrib.messages.add_message")
    def test_archive_view_cannot_be_accessed_for_archived_version(
        self, mocked_messages
    ):
        poll_version = factories.PollVersionFactory(state=constants.ARCHIVED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "archive", poll_version.pk
        )

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertRedirectsToVersionList(response, poll_version)

        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], messages.ERROR)
        self.assertEqual(mocked_messages.call_args[0][2], "Version cannot be archived")

        # status hasn't changed
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.ARCHIVED)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    @patch("django.contrib.messages.add_message")
    def test_archive_view_cannot_be_accessed_for_published_version(
        self, mocked_messages
    ):
        poll_version = factories.PollVersionFactory(state=constants.PUBLISHED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "archive", poll_version.pk
        )

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertRedirectsToVersionList(response, poll_version)

        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], messages.ERROR)
        self.assertEqual(mocked_messages.call_args[0][2], "Version cannot be archived")

        # status hasn't changed
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.PUBLISHED)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    @patch("django.contrib.messages.add_message")
    def test_archive_view_cannot_be_accessed_for_unpublished_version(
        self, mocked_messages
    ):
        poll_version = factories.PollVersionFactory(state=constants.UNPUBLISHED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "archive", poll_version.pk
        )

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertRedirectsToVersionList(response, poll_version)

        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], messages.ERROR)
        self.assertEqual(mocked_messages.call_args[0][2], "Version cannot be archived")

        # status hasn't changed
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.UNPUBLISHED)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    @patch("django.contrib.messages.add_message")
    def test_archive_view_redirects_when_nonexistent_version(self, mocked_messages):
        url = self.get_admin_url(self.versionable.version_model_proxy, "archive", 89)

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertRedirects(response, "/en/admin/", target_status_code=302)
        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], 30)  # warning level
        self.assertEqual(
            mocked_messages.call_args[0][2],
            'poll content version with ID "89" doesn\'t exist. Perhaps it was deleted?',
        )

    def test_archive_view_can_be_accessed_by_get_request(self):
        poll_version = factories.PollVersionFactory(state=constants.DRAFT)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "archive", poll_version.pk
        )

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request["REQUEST_METHOD"], "GET")
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.DRAFT)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)


class PublishViewTestCase(BaseStateTestCase):
    def setUp(self):
        self.versionable = PollsCMSConfig.versioning[0]

    def test_publish_view_doesnt_allow_user_without_staff_permissions(self):
        poll_version = factories.PollVersionFactory(state=constants.DRAFT)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "publish", poll_version.pk
        )
        with self.login_user_context(self.get_standard_user()):
            response = self.client.post(url)

        self.assertRedirects(response, admin_reverse("login") + "?next=" + url)
        # status hasn't changed
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.DRAFT)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    @freeze_time(None)
    @patch("django.contrib.admin.ModelAdmin.message_user")
    def test_publish_view_sets_state_and_redirects(self, mocked_messages):
        poll_version = factories.PollVersionFactory(state=constants.DRAFT)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "publish", poll_version.pk
        )
        user = self.get_staff_user_with_no_permissions()

        with self.login_user_context(user):
            response = self.client.post(url)

        # State updated
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.PUBLISHED)
        # State change tracked
        tracking = StateTracking.objects.get()
        self.assertEqual(tracking.version, poll_version_)
        self.assertEqual(tracking.date, now())
        self.assertEqual(tracking.old_state, constants.DRAFT)
        self.assertEqual(tracking.new_state, constants.PUBLISHED)
        self.assertEqual(tracking.user, user)
        # Message displayed
        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], "Version published")
        # Redirect happened
        self.assertRedirectsToVersionList(response, poll_version)

    def test_published_view_sets_modified_time(self):
        poll_version = factories.PollVersionFactory(state=constants.DRAFT)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "publish", poll_version.pk
        )
        user = self.get_staff_user_with_no_permissions()
        with freeze_time("2999-01-11 00:00:00", tz_offset=0), self.login_user_context(
            user
        ):
            self.client.post(url)

        # Refresh object after update
        poll_version.refresh_from_db(fields=["modified"])
        # check modified time is updated as freeze time
        self.assertEqual(
            poll_version.modified,
            datetime.datetime(2999, 1, 11, 00, 00, 00, tzinfo=utc),
        )

    @patch("django.contrib.messages.add_message")
    def test_publish_view_cannot_be_accessed_for_archived_version(
        self, mocked_messages
    ):
        poll_version = factories.PollVersionFactory(state=constants.ARCHIVED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "publish", poll_version.pk
        )

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertRedirectsToVersionList(response, poll_version)

        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], messages.ERROR)
        self.assertEqual(mocked_messages.call_args[0][2], "Version cannot be published")

        # status hasn't changed
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.ARCHIVED)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    @patch("django.contrib.messages.add_message")
    def test_publish_view_cannot_be_accessed_for_published_version(
        self, mocked_messages
    ):
        poll_version = factories.PollVersionFactory(state=constants.PUBLISHED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "publish", poll_version.pk
        )

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertRedirectsToVersionList(response, poll_version)

        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], messages.ERROR)
        self.assertEqual(mocked_messages.call_args[0][2], "Version cannot be published")

        # status hasn't changed
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.PUBLISHED)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    @patch("django.contrib.messages.add_message")
    def test_publish_view_cannot_be_accessed_for_unpublished_version(
        self, mocked_messages
    ):
        poll_version = factories.PollVersionFactory(state=constants.UNPUBLISHED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "publish", poll_version.pk
        )

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertRedirectsToVersionList(response, poll_version)

        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], messages.ERROR)
        self.assertEqual(mocked_messages.call_args[0][2], "Version cannot be published")

        # status hasn't changed
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.UNPUBLISHED)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    @patch("django.contrib.messages.add_message")
    def test_publish_view_redirects_when_nonexistent_version(self, mocked_messages):
        url = self.get_admin_url(self.versionable.version_model_proxy, "publish", 89)

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertRedirects(response, "/en/admin/", target_status_code=302)
        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], 30)  # warning level
        self.assertEqual(
            mocked_messages.call_args[0][2],
            'poll content version with ID "89" doesn\'t exist. Perhaps it was deleted?',
        )

    def test_publish_view_cant_be_accessed_by_get_request(self):
        poll_version = factories.PollVersionFactory(state=constants.DRAFT)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "publish", poll_version.pk
        )

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response._headers.get("allow"), ("Allow", "POST"))
        # status hasn't changed
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.DRAFT)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)


class UnpublishViewTestCase(BaseStateTestCase):
    def setUp(self):
        self.versionable = PollsCMSConfig.versioning[0]

    def test_unpublish_view_doesnt_allow_user_without_staff_permissions(self):
        poll_version = factories.PollVersionFactory(state=constants.PUBLISHED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "unpublish", poll_version.pk
        )
        with self.login_user_context(self.get_standard_user()):
            response = self.client.post(url)

        self.assertRedirects(response, admin_reverse("login") + "?next=" + url)
        # status hasn't changed
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.PUBLISHED)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    @freeze_time(None)
    @patch("django.contrib.admin.ModelAdmin.message_user")
    def test_unpublish_view_sets_state_and_redirects(self, mocked_messages):
        poll_version = factories.PollVersionFactory(state=constants.PUBLISHED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "unpublish", poll_version.pk
        )
        user = self.get_staff_user_with_no_permissions()

        with self.login_user_context(user):
            response = self.client.post(url)

        # State updated
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.UNPUBLISHED)
        # State change tracked
        tracking = StateTracking.objects.get()
        self.assertEqual(tracking.version, poll_version_)
        self.assertEqual(tracking.date, now())
        self.assertEqual(tracking.old_state, constants.PUBLISHED)
        self.assertEqual(tracking.new_state, constants.UNPUBLISHED)
        self.assertEqual(tracking.user, user)
        # Message displayed
        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], "Version unpublished")
        # Redirect happened
        self.assertRedirectsToVersionList(response, poll_version)

    def test_unpublish_view_sets_modified_time(self):
        poll_version = factories.PollVersionFactory(state=constants.PUBLISHED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "unpublish", poll_version.pk
        )
        user = self.get_staff_user_with_no_permissions()
        with freeze_time("2999-01-11 00:00:00", tz_offset=0), self.login_user_context(
            user
        ):
            self.client.post(url)

        # Refresh object after update
        poll_version.refresh_from_db(fields=["modified"])
        # check modified time is updated as freeze time
        self.assertEqual(
            poll_version.modified,
            datetime.datetime(2999, 1, 11, 00, 00, 00, tzinfo=utc),
        )

    @patch("django.contrib.messages.add_message")
    def test_unpublish_view_cannot_be_accessed_for_archived_version(
        self, mocked_messages
    ):
        poll_version = factories.PollVersionFactory(state=constants.ARCHIVED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "unpublish", poll_version.pk
        )

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertRedirectsToVersionList(response, poll_version)

        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], messages.ERROR)
        self.assertEqual(
            mocked_messages.call_args[0][2], "Version cannot be unpublished"
        )

        # status hasn't changed
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.ARCHIVED)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    @patch("django.contrib.messages.add_message")
    def test_unpublish_view_cannot_be_accessed_for_unpublished_version(
        self, mocked_messages
    ):
        poll_version = factories.PollVersionFactory(state=constants.UNPUBLISHED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "unpublish", poll_version.pk
        )

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertRedirectsToVersionList(response, poll_version)

        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], messages.ERROR)
        self.assertEqual(
            mocked_messages.call_args[0][2], "Version cannot be unpublished"
        )

        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    @patch("django.contrib.messages.add_message")
    def test_unpublish_view_cannot_be_accessed_for_draft_version(self, mocked_messages):
        poll_version = factories.PollVersionFactory(state=constants.DRAFT)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "unpublish", poll_version.pk
        )

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertRedirectsToVersionList(response, poll_version)

        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], messages.ERROR)
        self.assertEqual(
            mocked_messages.call_args[0][2], "Version cannot be unpublished"
        )

        # status hasn't changed
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.DRAFT)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    @patch("django.contrib.messages.add_message")
    def test_unpublish_view_redirects_when_nonexistent_version(self, mocked_messages):
        url = self.get_admin_url(self.versionable.version_model_proxy, "unpublish", 89)

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertRedirects(response, "/en/admin/", target_status_code=302)
        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], 30)  # warning level
        self.assertEqual(
            mocked_messages.call_args[0][2],
            'poll content version with ID "89" doesn\'t exist. Perhaps it was deleted?',
        )

    def test_unpublish_view_can_be_accessed_by_get_request(self):
        poll_version = factories.PollVersionFactory(state=constants.PUBLISHED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "unpublish", poll_version.pk
        )

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request["REQUEST_METHOD"], "GET")
        # status hasn't changed
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.PUBLISHED)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    def test_unpublish_view_uses_setting_to_populate_context(self):
        poll_version = factories.PollVersionFactory(state=constants.PUBLISHED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "unpublish", poll_version.pk
        )

        def unpublish_context1(request, version, *args, **kwargs):
            return "Don't unpublish cats. Seriously."

        def unpublish_context2(request, version, *args, **kwargs):
            return "Unpublish the mice instead."

        def publish_context(request, version, *args, **kwargs):
            return (
                "Publish cat pictures only. People aren't interested in anything else."
            )

        versioning_ext = apps.get_app_config("djangocms_versioning").cms_extension
        extra_context_setting = {
            "unpublish": OrderedDict(
                [("cats", unpublish_context1), ("mice", unpublish_context2)]
            ),
            "publish": OrderedDict([("cat_pictures", publish_context)]),
        }

        with patch.object(versioning_ext, "add_to_context", extra_context_setting):
            with self.login_user_context(self.get_staff_user_with_no_permissions()):
                response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("extra_context", response.context.keys())
        expected = OrderedDict(
            [
                ("cats", "Don't unpublish cats. Seriously."),
                ("mice", "Unpublish the mice instead."),
            ]
        )
        self.assertDictEqual(response.context["extra_context"], expected)
        self.assertIn("Don&#39;t unpublish cats. Seriously.", str(response.content))
        self.assertIn("Unpublish the mice instead.", str(response.content))
        self.assertNotIn("Publish cat pictures only.", str(response.content))

    def test_unpublish_view_doesnt_throw_exception_if_no_app_registered_extra_unpublish_context(
        self
    ):
        poll_version = factories.PollVersionFactory(state=constants.PUBLISHED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "unpublish", poll_version.pk
        )
        versioning_ext = apps.get_app_config("djangocms_versioning").cms_extension

        with patch.object(versioning_ext, "add_to_context", {}):
            with self.login_user_context(self.get_staff_user_with_no_permissions()):
                response = self.client.get(url)

        self.assertEqual(response.status_code, 200)


class RevertViewTestCase(BaseStateTestCase):
    def setUp(self):
        self.versionable = PollsCMSConfig.versioning[0]

    def test_revert_view_sets_modified_time(self):
        poll_version = factories.PollVersionFactory(state=constants.ARCHIVED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "revert", poll_version.pk
        )
        user = self.get_staff_user_with_no_permissions()
        with freeze_time("2999-01-11 00:00:00", tz_offset=0), self.login_user_context(
            user
        ):
            self.client.post(url)

        # get the new reverted draft object
        poll_version_ = Version.objects.filter(state=constants.DRAFT).first()
        # check modified time is updated as freeze time
        self.assertEqual(
            poll_version_.modified,
            datetime.datetime(2999, 1, 11, 00, 00, 00, tzinfo=utc),
        )


class EditRedirectTestCase(BaseStateTestCase):
    def setUp(self):
        self.versionable = PollsCMSConfig.versioning[0]
        self.superuser = self.get_superuser()

    def test_edit_redirect_view_doesnt_allow_user_without_staff_permissions(self):
        poll_version = factories.PollVersionFactory(state=constants.PUBLISHED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "edit_redirect", poll_version.pk
        )
        with self.login_user_context(self.get_standard_user()):
            response = self.client.post(url)

        self.assertRedirects(response, admin_reverse("login") + "?next=" + url)
        # no draft was created
        self.assertFalse(Version.objects.filter(state=constants.DRAFT).exists())

    @freeze_time(None)
    def test_edit_redirect_view_creates_draft_and_redirects(self):
        """If the version is published then create a draft and redirect
        to editing it.
        """
        published = factories.PollVersionFactory(state=constants.PUBLISHED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "edit_redirect", published.pk
        )
        user = self.get_staff_user_with_no_permissions()

        with self.login_user_context(user):
            response = self.client.post(url)

        # Draft created
        draft = Version.objects.get(state=constants.DRAFT)
        self.assertEqual(draft.content.poll, published.content.poll)
        self.assertEqual(draft.created_by, user)
        self.assertEqual(draft.created, now())
        # Content copied
        self.assertNotEqual(draft.content.pk, published.content.pk)
        self.assertEqual(draft.content.text, published.content.text)
        self.assertEqual(draft.content.language, published.content.language)
        # Redirect happened
        redirect_url = self.get_admin_url(PollContent, "change", draft.content.pk)
        self.assertRedirects(response, redirect_url, target_status_code=302)

    def test_edit_redirect_view_doesnt_create_draft_if_draft_exists(self):
        """If the version is published, but there is a newer version
        that is a draft then redirect to editing the draft, don't create.
        """
        draft = factories.PollVersionFactory(state=constants.DRAFT)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "edit_redirect", draft.pk
        )
        user = self.get_staff_user_with_no_permissions()

        with self.login_user_context(user):
            response = self.client.post(url)

        # No drafts created
        self.assertFalse(Version.objects.exclude(pk=draft.pk).exists())
        # Redirect happened
        redirect_url = self.get_admin_url(PollContent, "change", draft.content.pk)
        self.assertRedirects(response, redirect_url, target_status_code=302)

    def test_edit_redirect_view_url_uses_content_id_not_version_id(self):
        """Regression test for a bug. Make sure than when we generate
        the redirect url for the content change page, we use the id
        of the content record, not the id of the version record.
        """
        # All versions are stored in the version table so increase the
        # id of version id sequence by creating a blogpost version
        factories.BlogPostVersionFactory()
        # Now create a poll version - the poll content and version id
        # will be different.
        draft = factories.PollVersionFactory(state=constants.DRAFT)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "edit_redirect", draft.pk
        )
        user = self.get_staff_user_with_no_permissions()

        with self.login_user_context(user):
            response = self.client.post(url)

        # Redirect happened
        redirect_url = self.get_admin_url(PollContent, "change", draft.content.pk)
        self.assertRedirects(response, redirect_url, target_status_code=302)

    @patch("django.contrib.messages.add_message")
    def test_edit_redirect_view_cannot_be_accessed_for_archived_version(
        self, mocked_messages
    ):
        poll_version = factories.PollVersionFactory(state=constants.ARCHIVED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "edit_redirect", poll_version.pk
        )

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertRedirectsToVersionList(response, poll_version)

        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], messages.ERROR)
        self.assertEqual(
            mocked_messages.call_args[0][2],
            "Version is not in draft or published state",
        )

        # no draft was created
        self.assertFalse(Version.objects.filter(state=constants.DRAFT).exists())

    @patch("django.contrib.messages.add_message")
    def test_edit_redirect_view_cannot_be_accessed_for_unpublished_version(
        self, mocked_messages
    ):
        poll_version = factories.PollVersionFactory(state=constants.UNPUBLISHED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "edit_redirect", poll_version.pk
        )

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertRedirectsToVersionList(response, poll_version)

        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], messages.ERROR)
        self.assertEqual(
            mocked_messages.call_args[0][2],
            "Version is not in draft or published state",
        )

        # no draft was created
        self.assertFalse(Version.objects.filter(state=constants.DRAFT).exists())

    def test_edit_redirect_view_redirects_to_draft_for_published_version_when_draft_exists(
        self
    ):
        published = factories.PollVersionFactory(
            state=constants.PUBLISHED, content__language="en"
        )
        draft = factories.PollVersionFactory(
            state=constants.DRAFT,
            content__poll=published.content.poll,
            content__language="en",
        )
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "edit_redirect", published.pk
        )

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        # redirect happened
        redirect_url = self.get_admin_url(PollContent, "change", draft.content.pk)
        self.assertRedirects(response, redirect_url, target_status_code=302)
        # no draft was created
        self.assertFalse(
            Version.objects.exclude(pk=draft.pk).filter(state=constants.DRAFT).exists()
        )

    def test_edit_redirect_view_editable_object_endpoint(self):
        """
        An editable object should use the correct cms editable endpoint
        """
        pagecontent = factories.PageVersionFactory()
        versionable_pagecontent = VersioningCMSConfig.versioning[0]
        url = self.get_admin_url(
            versionable_pagecontent.version_model_proxy, "edit_redirect", pagecontent.pk
        )
        target_url = get_object_edit_url(pagecontent.content)

        with self.login_user_context(self.superuser):
            response = self.client.post(url)

        self.assertRedirects(response, target_url, target_status_code=302)

    def test_edit_redirect_view_non_editable_object_endpoint(self):
        """
        A non editable object should use the correct internally generated endpoint
        """
        poll_version = factories.PollVersionFactory()
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "edit_redirect", poll_version.pk
        )
        target_url = self.get_admin_url(PollContent, "change", poll_version.content.pk)

        with self.login_user_context(self.superuser):
            response = self.client.post(url)

        self.assertRedirects(response, target_url, target_status_code=302)

    @patch("django.contrib.messages.add_message")
    def test_edit_redirect_view_handles_nonexistent_version(self, mocked_messages):
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "edit_redirect", 89
        )

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertEqual(response.status_code, 404)
        # no draft was created
        self.assertFalse(Version.objects.filter(state=constants.DRAFT).exists())

    def test_edit_redirect_view_cant_be_accessed_by_get_request(self):
        poll_version = factories.PollVersionFactory(state=constants.PUBLISHED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "edit_redirect", poll_version.pk
        )

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response._headers.get("allow"), ("Allow", "POST"))
        # no draft was created
        self.assertFalse(Version.objects.filter(state=constants.DRAFT).exists())


class CompareViewTestCase(CMSTestCase):
    def setUp(self):
        self.versionable = PollsCMSConfig.versioning[0]
        self.disable_toolbar_params = {
            get_cms_setting("CMS_TOOLBAR_URL__DISABLE"): "1",
            get_cms_setting("CMS_TOOLBAR_URL__PERSIST"): "0",
        }

    def test_compare_view_doesnt_allow_user_without_staff_permissions(self):
        version = factories.PollVersionFactory()
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "compare", version.pk
        )
        with self.login_user_context(self.get_standard_user()):
            response = self.client.get(url)

        self.assertRedirects(response, admin_reverse("login") + "?next=" + url)

    def test_compare_view_has_version_data_in_context_when_no_get_param(self):
        """When the url for the compare view has no additional params
        version 2 can't be in the context (since we don't know what it
        is yet). So checking we have version 1 and a list of versions
        for the dropdown in context.
        """
        poll = factories.PollFactory()
        versions = factories.PollVersionFactory.create_batch(
            2, content__poll=poll, content__language="en"
        )
        factories.PollVersionFactory(
            content__poll=poll, content__language="fr"
        )  # Same grouper different language
        factories.PollVersionFactory(
            content__language="fr"
        )  # different grouper and different language
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "compare", versions[0].pk
        )
        user = self.get_staff_user_with_no_permissions()

        with self.login_user_context(user):
            response = self.client.get(url)

        context = response.context
        self.assertIn("v1", context)
        self.assertEqual(context["v1"], versions[0])
        self.assertIn("v1_preview_url", context)
        v1_preview_url = reverse(
            "admin:cms_placeholder_render_object_preview",
            args=(versions[0].content_type_id, versions[0].object_id),
        )
        parsed = urlparse(context["v1_preview_url"])
        self.assertEqual(parsed.path, v1_preview_url)
        self.assertEqual(
            {k: v[0] for k, v in parse_qs(parsed.query).items()},
            self.disable_toolbar_params,
        )
        self.assertNotIn("v2", context)
        self.assertNotIn("v2_preview_url", context)
        self.assertIn("version_list", context)
        self.assertQuerysetEqual(
            context["version_list"],
            [versions[0].pk, versions[1].pk],
            transform=lambda o: o.pk,
            ordered=False,
        )

    def test_compare_view_has_version_data_in_context_when_version2_in_get_param(self):
        """When the url for the compare view does have the compare_to
        GET param we should have all the same params in context as in
        the test above and also version 2.
        """
        poll = factories.PollFactory()
        versions = factories.PollVersionFactory.create_batch(
            3, content__poll=poll, content__language="en"
        )
        factories.PollVersionFactory(
            content__poll=poll, content__language="fr"
        )  # Same grouper different language
        factories.PollVersionFactory(
            content__language="fr"
        )  # different grouper and different language
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "compare", versions[0].pk
        )
        url += "?compare_to=%d" % versions[1].pk
        user = self.get_staff_user_with_no_permissions()

        with self.login_user_context(user):
            response = self.client.get(url)

        context = response.context
        self.assertIn("v1", context)
        self.assertEqual(context["v1"], versions[0])
        self.assertIn("v1_preview_url", context)
        v1_preview_url = reverse(
            "admin:cms_placeholder_render_object_preview",
            args=(versions[0].content_type_id, versions[0].object_id),
        )
        parsed = urlparse(context["v1_preview_url"])
        self.assertEqual(parsed.path, v1_preview_url)
        self.assertEqual(
            {k: v[0] for k, v in parse_qs(parsed.query).items()},
            self.disable_toolbar_params,
        )
        self.assertIn("v2", context)
        self.assertEqual(context["v2"], versions[1])
        self.assertIn("v2_preview_url", context)
        v2_preview_url = reverse(
            "admin:cms_placeholder_render_object_preview",
            args=(versions[1].content_type_id, versions[1].object_id),
        )
        parsed = urlparse(context["v2_preview_url"])
        self.assertEqual(parsed.path, v2_preview_url)
        self.assertEqual(
            {k: v[0] for k, v in parse_qs(parsed.query).items()},
            self.disable_toolbar_params,
        )
        self.assertIn("version_list", context)
        self.assertQuerysetEqual(
            context["version_list"],
            [versions[0].pk, versions[1].pk, versions[2].pk],
            transform=lambda o: o.pk,
            ordered=False,
        )

    @patch("django.contrib.messages.add_message")
    def test_edit_compare_view_handles_nonexistent_v1(self, mocked_messages):
        url = self.get_admin_url(self.versionable.version_model_proxy, "compare", 89)

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertRedirects(response, "/en/admin/", target_status_code=302)
        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], 30)  # warning level
        self.assertEqual(
            mocked_messages.call_args[0][2],
            'poll content version with ID "89" doesn\'t exist. Perhaps it was deleted?',
        )

    @patch("django.contrib.messages.add_message")
    def test_edit_compare_view_handles_nonexistent_v2(self, mocked_messages):
        version = factories.PollVersionFactory()
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "compare", version.pk
        )
        url += "?compare_to=134"

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertRedirects(response, "/en/admin/", target_status_code=302)
        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], 30)  # warning level
        self.assertEqual(
            mocked_messages.call_args[0][2],
            'poll content version with ID "134" doesn\'t exist. Perhaps it was deleted?',
        )


class VersionChangeListViewTestCase(CMSTestCase):
    def setUp(self):
        self.superuser = self.get_superuser()
        self.versionable = PollsCMSConfig.versioning[0]

    def test_no_querystring_shows_form(self):
        """Test that going to a changelist with no data in querystring
        shows a form to select a grouper.
        """
        pv = factories.PollVersionFactory()

        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.get_admin_url(self.versionable.version_model_proxy, "changelist"),
                follow=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertIn("poll", response.context["form"].fields)
        self.assertIn(
            (pv.content.poll.pk, str(pv.content.poll)),
            response.context["form"].fields["poll"].choices,
        )

    def test_missing_grouper(self):
        """Test that going to a changelist with no grouper in querystring
        shows an error.
        """
        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.get_admin_url(self.versionable.version_model_proxy, "changelist")
                + "?foo=1",
                follow=True,
            )

        self.assertRedirects(
            response, "/en/admin/djangocms_versioning/pollcontentversion/?e=1"
        )

    def test_grouper_filtering(self):
        pv = factories.PollVersionFactory()
        factories.PollVersionFactory.create_batch(4)

        with self.login_user_context(self.superuser):
            querystring = "?poll={grouper}".format(grouper=pv.content.poll_id)
            response = self.client.get(
                self.get_admin_url(self.versionable.version_model_proxy, "changelist")
                + querystring
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("cl", response.context)
        self.assertQuerysetEqual(
            response.context["cl"].queryset,
            [pv.pk],
            transform=lambda x: x.pk,
            ordered=False,
        )

    def test_changelist_view_displays_correct_breadcrumbs(self):
        poll_content = factories.PollContentWithVersionFactory()
        url = self.get_admin_url(self.versionable.version_model_proxy, "changelist")
        url += "?poll=" + str(poll_content.poll_id)

        with self.login_user_context(self.superuser):
            response = self.client.get(url)

        # Traverse the returned html to find the breadcrumbs
        soup = BeautifulSoup(str(response.content), features="lxml")
        breadcrumb_html = soup.find("div", class_="breadcrumbs")
        # Assert the breadcrumbs
        expected = """<div class="breadcrumbs">\\n<a href="/en/admin/">Home</a>\\n› """
        expected += """<a href="/en/admin/polls/">Polls</a>\\n› """
        expected += """<a href="/en/admin/polls/pollcontent/">Poll contents</a>\\n› """
        expected += """<a href="/en/admin/polls/pollcontent/{pk}/change/">{name}</a>\\n› """.format(
            pk=str(poll_content.pk), name=str(poll_content)
        )
        expected += """Versions\\n</div>"""
        self.assertEqual(str(breadcrumb_html), expected)

    def test_changelist_view_displays_correct_breadcrumbs_when_app_defines_breadcrumbs(
        self
    ):
        # The blogpost test app defines a breadcrumb template in
        # templates/admin/djangocms_versioning/blogpost/blogcontent/versioning_breadcrumbs.html
        # This test checks that template gets used.
        blog_content = factories.BlogContentWithVersionFactory()
        versionable = BlogpostCMSConfig.versioning[0]
        url = self.get_admin_url(versionable.version_model_proxy, "changelist")
        url += "?blogpost=" + str(blog_content.blogpost_id)

        with self.login_user_context(self.superuser):
            response = self.client.get(url)

        # Traverse the returned html to find the breadcrumbs
        soup = BeautifulSoup(str(response.content), features="lxml")
        breadcrumb_html = soup.find("div", class_="breadcrumbs")
        # Assert the breadcrumbs
        expected = """<div class="breadcrumbs">Blog post breadcrumbs bla bla</div>"""
        self.assertEqual(str(breadcrumb_html), expected)

    def test_changelist_view_displays_correct_breadcrumbs_for_extra_grouping_values(
        self
    ):
        with freeze_time("1999-09-09"):
            # Make sure the English version is older than the French
            # So that the French one is in fact the latest one
            page_content_en = factories.PageContentWithVersionFactory(language="en")
        factories.PageContentWithVersionFactory(
            language="fr", page=page_content_en.page
        )
        versionable = VersioningCMSConfig.versioning[0]
        url = self.get_admin_url(versionable.version_model_proxy, "changelist")
        # Specify English here - this should mean the version picked up
        # for the breadcrumbs is the English one, not the French one
        url += "?page={page_id}&language=en".format(
            page_id=str(page_content_en.page_id)
        )

        with self.login_user_context(self.superuser):
            response = self.client.get(url)

        # Traverse the returned html to find the breadcrumbs
        soup = BeautifulSoup(str(response.content), features="lxml")
        breadcrumb_html = soup.find("div", class_="breadcrumbs")
        # Assert the breadcrumbs - we should have ignored the French one
        # and put the English one in the breadcrumbs
        expected = """<div class="breadcrumbs">\\n<a href="/en/admin/">Home</a>\\n› """
        expected += """<a href="/en/admin/cms/">django CMS</a>\\n› """
        expected += """<a href="/en/admin/cms/pagecontent/">Page contents</a>\\n› """
        expected += """<a href="/en/admin/cms/pagecontent/{pk}/change/">{name}</a>\\n› """.format(
            pk=str(page_content_en.pk), name=str(page_content_en)
        )
        expected += """Versions\\n</div>"""
        self.assertEqual(str(breadcrumb_html), expected)

    def test_changelist_view_redirects_on_url_params_that_arent_grouping_params(self):
        # NOTE: Not sure this is really how the changelist should behave
        # but need a smoketest that it is not throwing errors it definitely shouldn't
        page_content = factories.PageContentWithVersionFactory()
        versionable = VersioningCMSConfig.versioning[0]
        url = self.get_admin_url(versionable.version_model_proxy, "changelist")
        url += "?title={title}&page={page_id}".format(
            title=page_content.title, page_id=str(page_content.page_id)
        )

        with self.login_user_context(self.superuser):
            response = self.client.get(url)

        expected_redirect = self.get_admin_url(
            versionable.version_model_proxy, "changelist"
        )
        expected_redirect += "?e=1"
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, expected_redirect)

    def test_changelist_view_redirects_on_url_params_that_dont_exist(self):
        # NOTE: Not sure this is really how the changelist should behave
        # but need a smoketest that it is not throwing errors it definitely shouldn't
        page_content = factories.PageContentWithVersionFactory()
        versionable = VersioningCMSConfig.versioning[0]
        url = self.get_admin_url(versionable.version_model_proxy, "changelist")
        url += "?crocodiles=true&page=" + str(page_content.page_id)

        with self.login_user_context(self.superuser):
            response = self.client.get(url)

        expected_redirect = self.get_admin_url(
            versionable.version_model_proxy, "changelist"
        )
        expected_redirect += "?e=1"
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, expected_redirect)

    def test_changelist_view_requires_change_permission(self):
        page_content = factories.PageContentWithVersionFactory()
        versionable = VersioningCMSConfig.versioning[0]
        url = self.get_admin_url(versionable.version_model_proxy, "changelist")
        url += "?page=" + str(page_content.page_id)

        with self.login_user_context(self.get_standard_user()):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            "/en/admin/login/?next=/en/admin/djangocms_versioning/pagecontentversion/%3Fpage%3D{}".format(
                page_content.pk
            ),
        )

    def test_change_view_cannot_be_accessed(self):
        page_content = factories.PageContentWithVersionFactory()
        versionable = VersioningCMSConfig.versioning[0]
        url = self.get_admin_url(
            versionable.version_model_proxy, "change", page_content.pk
        )

        with self.login_user_context(self.get_superuser()):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 403)


class VersionChangeViewTestCase(CMSTestCase):
    def setUp(self):
        self.versionable = PollsCMSConfig.versioning[0]
        self.superuser = self.get_superuser()

    def test_change_view_returns_200_for_draft(self):
        content = factories.PollContentWithVersionFactory(
            version__state=constants.DRAFT
        )
        url = self.get_admin_url(PollContent, "change", content.pk)

        with self.login_user_context(self.superuser):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_change_view_returns_readonly_for_published(self):
        content = factories.PollContentWithVersionFactory(
            version__state=constants.PUBLISHED
        )
        url = self.get_admin_url(PollContent, "change", content.pk)

        with self.login_user_context(self.superuser):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(flatten_fieldsets(response.context["adminform"].fieldsets)),
            set(response.context["adminform"].readonly_fields),
        )

    def test_change_view_returns_readonly_for_unpublished(self):
        content = factories.PollContentWithVersionFactory(
            version__state=constants.UNPUBLISHED
        )
        url = self.get_admin_url(PollContent, "change", content.pk)

        with self.login_user_context(self.superuser):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(flatten_fieldsets(response.context["adminform"].fieldsets)),
            set(response.context["adminform"].readonly_fields),
        )

    def test_change_view_returns_readonly_for_archived(self):
        content = factories.PollContentWithVersionFactory(
            version__state=constants.ARCHIVED
        )
        url = self.get_admin_url(PollContent, "change", content.pk)

        with self.login_user_context(self.superuser):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(flatten_fieldsets(response.context["adminform"].fieldsets)),
            set(response.context["adminform"].readonly_fields),
        )

    @patch("django.contrib.messages.add_message")
    def test_change_view_redirects_for_nonexistent_object(self, mocked_messages):
        url = self.get_admin_url(PollContent, "change", 144)

        with self.login_user_context(self.superuser):
            response = self.client.get(url)

        self.assertRedirects(response, "/en/admin/", target_status_code=302)
        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], 30)  # warning level
        self.assertEqual(
            mocked_messages.call_args[0][2],
            'poll content with ID "144" doesn\'t exist. Perhaps it was deleted?',
        )

    def test_change_view_action_compare_versions_one_selected(self):
        """
        A validation message is shown when one versioning option is selected
        to compare
        """
        poll = factories.PollFactory()
        factories.PollVersionFactory.create_batch(4, content__poll=poll)
        querystring = "?poll={grouper}".format(grouper=poll.pk)
        endpoint = (
            self.get_admin_url(self.versionable.version_model_proxy, "changelist")
            + querystring
        )

        with self.login_user_context(self.superuser):
            data = {
                "action": "compare_versions",
                admin.ACTION_CHECKBOX_NAME: ["2"],
                "post": "yes",
            }
            response = self.client.post(endpoint, data, follow=True)

        self.assertContains(response, "Exactly two versions need to be selected.")

    def test_change_view_action_compare_versions_two_selected(self):
        """
        The user is redirectd to the compare view with two versions selected
        """
        poll = factories.PollFactory()
        factories.PollVersionFactory.create_batch(4, content__poll=poll)
        querystring = "?poll={grouper}".format(grouper=poll.pk)
        endpoint = (
            self.get_admin_url(self.versionable.version_model_proxy, "changelist")
            + querystring
        )
        success_redirect = self.get_admin_url(
            self.versionable.version_model_proxy, "compare", 1
        )
        success_redirect += "?compare_to=2"

        with self.login_user_context(self.superuser):
            data = {
                "action": "compare_versions",
                admin.ACTION_CHECKBOX_NAME: ["1", "2"],
                "post": "yes",
            }
            response = self.client.post(endpoint, data, follow=True)

        self.assertNotContains(response, "Two versions have to be selected.")
        self.assertRedirects(response, success_redirect, status_code=302)

    def test_change_view_action_compare_versions_three_selected(self):
        """
        A validation message is shown when three versioning options are selected
        to compare
        """
        poll = factories.PollFactory()
        factories.PollVersionFactory.create_batch(4, content__poll=poll)
        querystring = "?poll={grouper}".format(grouper=poll.pk)
        endpoint = (
            self.get_admin_url(self.versionable.version_model_proxy, "changelist")
            + querystring
        )

        with self.login_user_context(self.superuser):
            data = {
                "action": "compare_versions",
                admin.ACTION_CHECKBOX_NAME: ["1", "2", "3"],
                "post": "yes",
            }
            response = self.client.post(endpoint, data, follow=True)

        self.assertContains(response, "Exactly two versions need to be selected.")
