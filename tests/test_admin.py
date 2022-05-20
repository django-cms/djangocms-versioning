import datetime
import re
import warnings
from collections import OrderedDict
from unittest import skip
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

from django.apps import apps
from django.contrib import admin, messages
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.admin.utils import flatten_fieldsets
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory
from django.test.utils import ignore_warnings
from django.urls import reverse
from django.utils.formats import localize
from django.utils.timezone import now

from cms.test_utils.testcases import CMSTestCase
from cms.toolbar.utils import get_object_edit_url, get_object_preview_url
from cms.utils.conf import get_cms_setting
from cms.utils.helpers import is_editable_model
from cms.utils.urlutils import admin_reverse

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
from djangocms_versioning.compat import DJANGO_GTE_30
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
                check_obj.created, datetime.datetime(2011, 1, 6)
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
            factories.PollContentWithVersionFactory.create_batch(2, poll=poll1, language="en")
            factories.PollContentWithVersionFactory(poll=poll2, language="en")
        # For these the created date will be now
        poll_content1 = factories.PollContentWithVersionFactory(poll=poll1, language="en")
        poll_content2 = factories.PollContentWithVersionFactory(poll=poll2, language="en")
        poll_content3 = factories.PollContentWithVersionFactory(language="en")

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

    def test_default_changelist_view_language_on_polls_with_language_content(self):
        """A multi lingual model shows the correct values when
        language filters / additional grouping values are set
        using the default content changelist overriden by VersioningChangeListMixin
        """
        changelist_url = self.get_admin_url(PollContent, "changelist")
        poll = factories.PollFactory()
        en_version1 = factories.PollVersionFactory(content__poll=poll, content__language="en")
        fr_version1 = factories.PollVersionFactory(content__poll=poll, content__language="fr")

        with self.login_user_context(self.get_superuser()):
            en_response = self.client.get(changelist_url, {"language": "en", "poll": poll.pk})
            fr_response = self.client.get(changelist_url, {"language": "fr", "poll": poll.pk})

        # English values checked
        self.assertEqual(200, en_response.status_code)
        self.assertEqual(1, en_response.context["cl"].queryset.count())
        self.assertEqual(en_version1.content, en_response.context["cl"].queryset.first())
        # French values checked
        self.assertEqual(200, fr_response.status_code)
        self.assertEqual(1, fr_response.context["cl"].queryset.count())
        self.assertEqual(fr_version1.content, fr_response.context["cl"].queryset.first())


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

    def test_discard_version_through_post_action(self):
        """
        Discard the last version redirects to changelist
        """
        version = factories.PollVersionFactory(state=constants.DRAFT)
        draft_discard_url = self.get_admin_url(
            self.versionable.version_model_proxy, "discard", version.pk
        )
        request = RequestFactory().post(draft_discard_url, {'discard': '1'})
        request.user = factories.UserFactory()

        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)

        redirect = self.version_admin.discard_view(request, str(version.pk))
        changelist_url = helpers.get_admin_url(version.content.__class__, 'changelist')

        self.assertEqual(redirect.status_code, 302)
        self.assertEqual(redirect.url, changelist_url)

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
            datetime.datetime(2999, 1, 11, 00, 00, 00),
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

        # Django < 3 support
        if not DJANGO_GTE_30:
            self.assertEqual(
                mocked_messages.call_args[0][2],
                'poll content version with ID "89" doesn\'t exist. Perhaps it was deleted?',
            )
        # django >= 3 support
        else:
            self.assertEqual(
                mocked_messages.call_args[0][2],
                "poll content version with ID “89” doesn’t exist. Perhaps it was deleted?",
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
            datetime.datetime(2999, 1, 11, 00, 00, 00),
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

        # Django < 3 support
        if not DJANGO_GTE_30:
            self.assertEqual(
                mocked_messages.call_args[0][2],
                'poll content version with ID "89" doesn\'t exist. Perhaps it was deleted?',
            )
        # django >= 3 support
        else:
            self.assertEqual(
                mocked_messages.call_args[0][2],
                "poll content version with ID “89” doesn’t exist. Perhaps it was deleted?",
            )

    def test_publish_view_cant_be_accessed_by_get_request(self):
        poll_version = factories.PollVersionFactory(state=constants.DRAFT)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, "publish", poll_version.pk
        )

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 405)

        # Django 2.2 backwards compatibility
        if hasattr(response, '_headers'):
            self.assertEqual(response._headers.get("allow"), ("Allow", "POST"))
        else:
            self.assertEqual(response.headers.get("Allow"), "POST")

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
            datetime.datetime(2999, 1, 11, 00, 00, 00),
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

        # Django < 3 support
        if not DJANGO_GTE_30:
            self.assertEqual(
                mocked_messages.call_args[0][2],
                'poll content version with ID "89" doesn\'t exist. Perhaps it was deleted?',
            )
        # django >= 3 support
        else:
            self.assertEqual(
                mocked_messages.call_args[0][2],
                "poll content version with ID “89” doesn’t exist. Perhaps it was deleted?",
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

        # Django < 3 support
        if not DJANGO_GTE_30:
            self.assertIn("Don&#39;t unpublish cats. Seriously.", str(response.content))
        # django >= 3 support
        else:
            self.assertIn("Don&#x27;t unpublish cats. Seriously.", str(response.content))

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
            datetime.datetime(2999, 1, 11, 00, 00, 00),
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
        An editable object should use the correct cms editable endpoint dependant on the
        contents language.

        It is important to use the correct language on the endpoint because any plugins will be
        added by the cms in that language.
        """
        versionable_pagecontent = VersioningCMSConfig.versioning[0]
        # A content object with a default language, be sure to use the languages endpoint
        en_pagecontent = factories.PageVersionFactory(content__language="en")
        en_url = self.get_admin_url(
            versionable_pagecontent.version_model_proxy, "edit_redirect", en_pagecontent.pk
        )
        en_target_url = get_object_edit_url(en_pagecontent.content, language="en")
        # Another content object with a different language, be sure to use the objects language endpoint
        it_pagecontent = factories.PageVersionFactory(content__language="it")
        it_url = self.get_admin_url(
            versionable_pagecontent.version_model_proxy, "edit_redirect", it_pagecontent.pk
        )
        it_target_url = get_object_edit_url(it_pagecontent.content, language="it")

        with self.login_user_context(self.superuser):
            en_response = self.client.post(en_url)
            it_response = self.client.post(it_url)

        self.assertRedirects(en_response, en_target_url, target_status_code=302)
        self.assertRedirects(it_response, it_target_url, target_status_code=302)

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

        # Django 2.2 backwards compatibility
        if hasattr(response, '_headers'):
            self.assertEqual(response._headers.get("allow"), ("Allow", "POST"))
        else:
            self.assertEqual(response.headers.get("Allow"), "POST")

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

        self.assertContains(response, "Version #{number} ({date})".format(
            number=versions[0].number, date=localize(versions[0].created)))

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
        # Same grouper and different language
        factories.PollVersionFactory(
            content__poll=poll, content__language="fr"
        )
        # different grouper and different language
        factories.PollVersionFactory(
            content__language="fr"
        )

        url = self.get_admin_url(
            self.versionable.version_model_proxy, "compare", versions[0].pk
        )
        url += "?compare_to=%d" % versions[1].pk
        user = self.get_staff_user_with_no_permissions()

        with self.login_user_context(user):
            response = self.client.get(url)

        self.assertContains(response, "Comparing Version #{}".format(versions[0].number))
        self.assertContains(response, "Version #{}".format(versions[0].number))
        self.assertContains(response, "Version #{}".format(versions[1].number))

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

        # Django < 3 support
        if not DJANGO_GTE_30:
            self.assertEqual(
                mocked_messages.call_args[0][2],
                'poll content version with ID "89" doesn\'t exist. Perhaps it was deleted?',
            )
        # django >= 3 support
        else:
            self.assertEqual(
                mocked_messages.call_args[0][2],
                "poll content version with ID “89” doesn’t exist. Perhaps it was deleted?",
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

        # Django < 3 support
        if not DJANGO_GTE_30:
            self.assertEqual(
                mocked_messages.call_args[0][2],
                'poll content version with ID "134" doesn\'t exist. Perhaps it was deleted?',
            )
        # django >= 3 support
        else:
            self.assertEqual(
                mocked_messages.call_args[0][2],
                "poll content version with ID “134” doesn’t exist. Perhaps it was deleted?",
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

    def test_missing_grouper_does_not_exist(self):
        """Go to changelist with a grouper that does not exist in querystring
        returns the status code 404. The grouper does not exist.
        """
        self.client.force_login(self.superuser)
        response = self.client.get(
            self.get_admin_url(self.versionable.version_model_proxy, "changelist")
            + "?poll=999",
            follow=True,
        )

        self.assertEqual(response.status_code, 404)

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

    def test_view_language_on_poll_with_no_language_content(self):
        """A multi lingual model shows an empty version list when no
        language filters / additional grouping values exist for the grouper
        """
        changelist_url = self.get_admin_url(self.versionable.version_model_proxy, "changelist")
        version = factories.PollVersionFactory(content__language="en")

        with self.login_user_context(self.get_superuser()):
            response = self.client.get(changelist_url, {"language": "fr", "poll": version.content.poll_id})

        self.assertEqual(200, response.status_code)
        self.assertEqual(0, response.context["cl"].queryset.count())

    def test_view_language_on_polls_with_language_content(self):
        """A multi lingual model shows the correct values when
        language filters / additional grouping values are set
        """
        changelist_url = self.get_admin_url(self.versionable.version_model_proxy, "changelist")
        poll = factories.PollFactory()
        en_version1 = factories.PollVersionFactory(content__poll=poll, content__language="en")
        fr_version1 = factories.PollVersionFactory(content__poll=poll, content__language="fr")

        with self.login_user_context(self.get_superuser()):
            fr_response = self.client.get(changelist_url, {"language": "fr", "poll": poll.pk})
            en_response = self.client.get(changelist_url, {"language": "en", "poll": poll.pk})

        # English values checked
        self.assertEqual(200, en_response.status_code)
        self.assertEqual(1, en_response.context["cl"].queryset.count())
        self.assertEqual(en_version1.content, en_response.context["cl"].queryset.first().content)
        # French values checked
        self.assertEqual(200, fr_response.status_code)
        self.assertEqual(1, fr_response.context["cl"].queryset.count())
        self.assertEqual(fr_version1.content, fr_response.context["cl"].queryset.first().content)

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
        user = self.get_staff_user_with_no_permissions()
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="djangocms_versioning",
                codename="change_pagecontentversion",
            )
        )
        page_content = factories.PageContentWithVersionFactory()
        versionable = VersioningCMSConfig.versioning[0]
        url = self.get_admin_url(versionable.version_model_proxy, "changelist")
        url += "?page=" + str(page_content.page_id)

        with self.login_user_context(user):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_changelist_view_user_doesnt_have_permission(self):
        page_content = factories.PageContentWithVersionFactory()
        versionable = VersioningCMSConfig.versioning[0]
        url = self.get_admin_url(versionable.version_model_proxy, "changelist")
        url += "?page=" + str(page_content.page_id)

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
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

        # Django < 3 support
        if not DJANGO_GTE_30:
            self.assertEqual(
                mocked_messages.call_args[0][2],
                'poll content with ID "144" doesn\'t exist. Perhaps it was deleted?',
            )
        # django >= 3 support
        else:
            self.assertEqual(
                mocked_messages.call_args[0][2],
                "poll content with ID “144” doesn’t exist. Perhaps it was deleted?",
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
                ACTION_CHECKBOX_NAME: ["2"],
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
                ACTION_CHECKBOX_NAME: ["1", "2"],
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
                ACTION_CHECKBOX_NAME: ["1", "2", "3"],
                "post": "yes",
            }
            response = self.client.post(endpoint, data, follow=True)

        self.assertContains(response, "Exactly two versions need to be selected.")


class ExtendedVersionAdminTestCase(CMSTestCase):

    def test_extended_version_change_list_display_renders_from_provided_list_display(self):
        """
        All fields are present for a content object if the class inheriting the mixin:
        ExtendedVersionAdminMixin has set any fields to display.
        This will be the list of fields the user has added and the fields & actions set by the mixin.
        """
        content = factories.PollContentFactory(language="en")
        factories.PollVersionFactory(content=content)

        with self.login_user_context(self.get_superuser()):
            response = self.client.get(self.get_admin_url(PollContent, "changelist"))

        # Check response is valid
        self.assertEqual(200, response.status_code)

        # Check list_display item is rendered
        self.assertContains(response, '<a href="?o=1">Text</a></div>')
        # Check list_action links are rendered
        self.assertContains(response, "cms-versioning-action-btn")
        self.assertContains(response, "cms-versioning-action-preview")
        self.assertContains(response, "cms-versioning-action-edit")
        self.assertContains(response, "cms-versioning-action-manage-versions")
        self.assertContains(response, "js-versioning-action")

    def test_extended_version_change_list_display_renders_without_list_display(self):
        """
        A default is set for the content object if the class inheriting the mixin:
        ExtendedVersionAdminMixin has not set any list_display fields.
        """
        factories.BlogContentWithVersionFactory()

        with self.login_user_context(self.get_superuser()):
            response = self.client.get(self.get_admin_url(BlogContent, "changelist"))

        # Check response is valid
        self.assertEqual(200, response.status_code)
        # Check for default value
        self.assertContains(response, 'class="field-__str__"')
        # Check list_action links are rendered
        self.assertContains(response, "cms-versioning-action-btn")
        self.assertContains(response, "cms-versioning-action-preview")
        self.assertContains(response, "cms-versioning-action-edit")
        self.assertContains(response, "cms-versioning-action-manage-versions")
        self.assertContains(response, "js-versioning-action")

    def test_extended_version_change_list_actions_burger_menu_available(self):
        """
        The actions burger menu should be available for anything that inherits ExtendedVersionAdminMixin.
        """
        content = factories.PollContentFactory(language="en")
        factories.PollVersionFactory(content=content)

        with self.login_user_context(self.get_superuser()):
            response = self.client.get(self.get_admin_url(PollContent, "changelist"))

        soup = BeautifulSoup(str(response.content), features="lxml")

        self.assertEqual(200, response.status_code)
        # action script exists and static path variable exists
        self.assertContains(response, "versioning_static_url_prefix")
        self.assertTrue(soup.find("script", src=re.compile("djangocms_versioning/js/actions.js")))


class ListActionsTestCase(CMSTestCase):
    def setUp(self):
        self.modeladmin = admin.site._registry[PollContent]

    def test_edit_link(self):
        """
        The edit link should be shown when a version is editable. A published version can show an edit button
        which causes a new draft to be created.
        """
        content_model = factories.BlogContentWithVersionFactory()
        version = content_model.versions.last()
        request = self.get_request("/")
        request.user = self.get_superuser()
        menu_content = version.content

        func = self.modeladmin._list_actions(request)
        edit_endpoint = reverse("admin:djangocms_versioning_pollcontentversion_edit_redirect", args=(version.pk,),)
        response = func(menu_content)

        self.assertIn("cms-versioning-action-btn", response)
        self.assertIn('title="Edit"', response)
        self.assertIn(edit_endpoint, response)

    def test_edit_link_inactive(self):
        """
        The edit link should not be shown for a user that does not have the edit permission.
        """
        content_model = factories.BlogContentWithVersionFactory()
        version = content_model.versions.last()
        request = self.get_request("/")
        request.user = self.get_staff_user_with_no_permissions()

        func = self.modeladmin._list_actions(request)
        edit_endpoint = reverse("admin:djangocms_versioning_blogcontentversion_edit_redirect", args=(version.pk,),)
        response = func(version.content)

        self.assertIn("inactive", response)
        self.assertIn('title="Edit"', response)
        self.assertNotIn(edit_endpoint, response)
