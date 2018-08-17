import datetime
import warnings
from unittest import skip
from unittest.mock import Mock, patch

from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.test import RequestFactory
from django.test.utils import ignore_warnings
from django.utils.timezone import now

from cms.test_utils.testcases import CMSTestCase
from cms.utils.urlutils import admin_reverse

import pytz
from freezegun import freeze_time

import djangocms_versioning.helpers
from djangocms_versioning import constants
from djangocms_versioning.admin import (
    VersionAdmin,
    VersionChangeList,
    VersioningAdminMixin,
)
from djangocms_versioning.helpers import (
    register_versionadmin_proxy,
    replace_admin_for_models,
    versioning_admin_factory,
)
from djangocms_versioning.models import StateTracking, Version
from djangocms_versioning.test_utils import factories
from djangocms_versioning.test_utils.blogpost.models import BlogContent
from djangocms_versioning.test_utils.polls.cms_config import PollsCMSConfig
from djangocms_versioning.test_utils.polls.models import (
    Answer,
    Poll,
    PollContent,
)


class AdminVersioningTestCase(CMSTestCase):

    def test_admin_factory(self):
        """Test that `versioning_admin_factory` creates a class based on
        provided admin class
        """
        admin_class = type('TestAdmin', (admin.ModelAdmin, ), {})

        new_admin_class = versioning_admin_factory(admin_class)
        mro = new_admin_class.mro()

        # both base classes are used
        self.assertTrue(issubclass(new_admin_class, admin_class))
        self.assertTrue(issubclass(new_admin_class, VersioningAdminMixin))

        # VersioningAdminMixin takes precedence over user-defined class
        self.assertTrue(mro.index(VersioningAdminMixin) < mro.index(admin_class))


class AdminReplaceVersioningTestCase(CMSTestCase):

    def setUp(self):
        self.model = Poll
        self.site = admin.AdminSite()
        self.admin_class = type('TestAdmin', (admin.ModelAdmin, ), {})

    def test_replace_admin_on_unregistered_model(self):
        """Test that calling `replace_admin_for_models` with a model that
        isn't registered in admin is a no-op.
        """
        replace_admin_for_models([self.model], self.site)

        self.assertNotIn(self.model, self.site._registry)

    def test_replace_admin_on_registered_models_default_site(self):
        with patch.object(djangocms_versioning.helpers, '_replace_admin_for_model') as mock:
            replace_admin_for_models([PollContent])

        mock.assert_called_with(admin.site._registry[PollContent], admin.site)

    def test_replace_admin_on_registered_models(self):
        self.site.register(self.model, self.admin_class)
        self.site.register(Answer, self.admin_class)
        models = [self.model, Answer]

        replace_admin_for_models(models, self.site)

        for model in models:
            self.assertIn(model, self.site._registry)
            self.assertIn(self.admin_class, self.site._registry[model].__class__.mro())
            self.assertIn(VersioningAdminMixin, self.site._registry[model].__class__.mro())

    def test_replace_default_admin_on_registered_model(self):
        """Test that registering a model without specifying own
        ModelAdmin class still results in overridden admin class.
        """
        self.site.register(self.model)

        replace_admin_for_models([self.model], self.site)

        self.assertIn(self.model, self.site._registry)
        self.assertIn(VersioningAdminMixin, self.site._registry[self.model].__class__.mro())

    def test_replace_admin_again(self):
        """Test that, if a model's admin class already subclasses
        VersioningAdminMixin, nothing happens.
        """
        version_admin = versioning_admin_factory(self.admin_class)
        self.site.register(self.model, version_admin)

        replace_admin_for_models([self.model], self.site)

        self.assertIn(self.model, self.site._registry)
        self.assertEqual(self.site._registry[self.model].__class__, version_admin)


class AdminAddVersionTestCase(CMSTestCase):

    def _get_admin_class_obj(self, content_model):
        """Helper method to set up a model admin class that derives
        from VersioningAdminMixin
        """
        admin_class = type(
            'VersioningModelAdmin', (VersioningAdminMixin, admin.ModelAdmin), {})
        admin_site = admin.AdminSite()
        return admin_class(model=content_model, admin_site=admin_site)

    def test_poll_version_is_added_for_change_false(self):
        model_admin = self._get_admin_class_obj(PollContent)
        with freeze_time('2011-01-06'):
            pc1 = factories.PollContentFactory()
            request = RequestFactory().get('/admin/polls/pollcontent/')
            request.user = factories.UserFactory()
            model_admin.save_model(request, pc1, form=None, change=False)
            check_obj = Version.objects.get(
                content_type=ContentType.objects.get_for_model(pc1),
                object_id=pc1.pk,
            )
            self.assertTrue(check_obj)
            self.assertEqual(check_obj.created, datetime.datetime(2011, 1, 6, tzinfo=pytz.utc))

    def test_poll_version_is_not_added_for_change_true(self):
        model_admin = self._get_admin_class_obj(PollContent)
        pc2 = factories.PollContentFactory()
        request = RequestFactory().get('/admin/polls/pollcontent/')
        model_admin.save_model(request, pc2, form=None, change=True)
        check_obj_exist = Version.objects.filter(
            content_type=ContentType.objects.get_for_model(pc2),
            object_id=pc2.pk).exists()
        self.assertFalse(check_obj_exist)

    def test_blogpost_version_is_added_for_change_false(self):
        model_admin = self._get_admin_class_obj(BlogContent)
        bc1 = factories.BlogContentFactory()
        request = RequestFactory().get('/admin/blogposts/blogcontent/')
        request.user = factories.UserFactory()
        model_admin.save_model(request, bc1, form=None, change=False)
        check_obj_exist = Version.objects.filter(
            content_type=ContentType.objects.get_for_model(bc1),
            object_id=bc1.pk).exists()
        self.assertTrue(check_obj_exist)

    def test_blogpost_version_is_not_added_for_change_true(self):
        model_admin = self._get_admin_class_obj(BlogContent)
        bc2 = factories.BlogContentFactory()
        request = RequestFactory().get('/admin/blogposts/blogcontent/')
        model_admin.save_model(request, bc2, form=None, change=True)
        check_obj_exist = Version.objects.filter(
            content_type=ContentType.objects.get_for_model(bc2),
            object_id=bc2.pk).exists()
        self.assertFalse(check_obj_exist)


class ContentAdminChangelistTestCase(CMSTestCase):

    def _get_admin_class_obj(self, content_model):
        """Helper method to set up a model admin class that derives
        from VersioningAdminMixin
        """
        admin_class = type(
            'VersioningModelAdmin', (VersioningAdminMixin, admin.ModelAdmin), {})
        admin_site = admin.AdminSite()
        return admin_class(model=content_model, admin_site=admin_site)

    def test_only_fetches_latest_content_records(self):
        """Returns content records of the latest content
        """
        model_admin = self._get_admin_class_obj(PollContent)
        poll1 = factories.PollFactory()
        poll2 = factories.PollFactory()
        # Make sure django sets the created date far in the past
        with freeze_time('2014-01-01'):
            factories.PollContentWithVersionFactory.create_batch(
                2, poll=poll1)
            factories.PollContentWithVersionFactory(poll=poll2)
        # For these the created date will be now
        poll_content1 = factories.PollContentWithVersionFactory(poll=poll1)
        poll_content2 = factories.PollContentWithVersionFactory(poll=poll2)
        poll_content3 = factories.PollContentWithVersionFactory()
        request = RequestFactory().get('/admin/polls/pollcontent/')

        admin_queryset = model_admin.get_queryset(request)

        self.assertQuerysetEqual(
            admin_queryset,
            [poll_content1.pk, poll_content2.pk, poll_content3.pk],
            transform=lambda x: x.pk,
            ordered=False
        )

    def test_records_filtering_is_generic(self):
        """Check there's nothing specific to polls hardcoded in
        VersioningAdminMixin.get_queryset. This repeats a similar test
        for PollContent, but using BlogContent instead.
        """
        model_admin = self._get_admin_class_obj(BlogContent)
        post = factories.BlogPostFactory()
        # Make sure django sets the created date far in the past
        with freeze_time('2016-06-06'):
            factories.BlogContentWithVersionFactory(blogpost=post)
        # For these the created date will be now
        blog_content1 = factories.BlogContentWithVersionFactory(blogpost=post)
        blog_content2 = factories.BlogContentWithVersionFactory()
        request = RequestFactory().get('/admin/blogpost/blogcontent/')

        admin_queryset = model_admin.get_queryset(request)

        self.assertQuerysetEqual(
            admin_queryset,
            [blog_content1.pk, blog_content2.pk],
            transform=lambda x: x.pk,
            ordered=False
        )


class AdminRegisterVersionTestCase(CMSTestCase):

    def test_register_version_admin(self):
        """Test that a model admin based on VersionAdmin class is registered
        for specified VersionableItem
        """
        site = admin.AdminSite()

        versionable = Mock(
            spec=[],
            version_model_proxy=Version,
            grouper_model=Poll,
        )
        register_versionadmin_proxy(versionable, site)

        self.assertIn(Version, site._registry)
        self.assertIn(VersionAdmin, site._registry[Version].__class__.mro())

    @ignore_warnings(module='djangocms_versioning.helpers')
    def test_register_version_admin_again(self):
        """Test that attempting to register a proxy model again
        doesn't do anything.
        """
        existing_admin = type('TestAdmin', (admin.ModelAdmin, ), {})
        site = admin.AdminSite()
        site.register(Version, existing_admin)
        versionable = Mock(
            spec=[],
            version_model_proxy=Version,
            grouper_model=Poll,
        )

        with patch.object(site, 'register') as mock:
            register_versionadmin_proxy(versionable, site)

        mock.assert_not_called()

    def test_register_versionadmin_proxy_warning(self):
        existing_admin = type('TestAdmin', (admin.ModelAdmin, ), {})
        site = admin.AdminSite()
        site.register(Version, existing_admin)
        versionable = Mock(
            spec=[],
            version_model_proxy=Version,
            grouper_model=Poll,
        )

        with patch.object(warnings, 'warn') as mock:
            register_versionadmin_proxy(versionable, site)
        message = '{!r} is already registered with admin.'.format(Version)
        mock.assert_called_with(message, UserWarning)


class VersionAdminTestCase(CMSTestCase):

    def setUp(self):
        self.site = admin.AdminSite()
        self.site.register(Version, VersionAdmin)

    def test_get_changelist(self):
        self.assertEqual(
            self.site._registry[Version].get_changelist(RequestFactory().get('/admin/')),
            VersionChangeList,
        )

    def test_queryset_content_prefetching(self):
        factories.PollVersionFactory.create_batch(4)
        with self.assertNumQueries(2):
            qs = self.site._registry[Version].get_queryset(RequestFactory().get('/'))
            for version in qs:
                version.content
        self.assertTrue(qs._prefetch_done)
        self.assertIn('content', qs._prefetch_related_lookups)

    def test_content_link(self):
        version = factories.PollVersionFactory(content__text='test4')
        self.assertEqual(
            self.site._registry[Version].content_link(version),
            '<a href="{url}">{label}</a>'.format(
                url='/en/admin/polls/pollcontent/1/change/',
                label='test4',
            ),
        )


class StateActionsTestCase(CMSTestCase):

    def test_archive_in_state_actions_for_draft_version(self):
        version = factories.PollVersionFactory(state=constants.DRAFT)
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == 'PollContentVersion'][0]
        archive_url = reverse(
            'admin:djangocms_versioning_pollcontentversion_archive',
            args=(version.pk,))

        state_actions = admin.site._registry[version_model_proxy].state_actions(version)

        self.assertIn(archive_url, state_actions)

    def test_archive_not_in_state_actions_for_archived_version(self):
        version = factories.PollVersionFactory(state=constants.ARCHIVED)
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == 'PollContentVersion'][0]
        archive_url = reverse(
            'admin:djangocms_versioning_pollcontentversion_archive',
            args=(version.pk,))

        state_actions = admin.site._registry[version_model_proxy].state_actions(version)

        self.assertNotIn(archive_url, state_actions)

    def test_archive_not_in_state_actions_for_published_version(self):
        version = factories.PollVersionFactory(state=constants.PUBLISHED)
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == 'PollContentVersion'][0]
        archive_url = reverse(
            'admin:djangocms_versioning_pollcontentversion_archive',
            args=(version.pk,))

        state_actions = admin.site._registry[version_model_proxy].state_actions(version)

        self.assertNotIn(archive_url, state_actions)

    def test_archive_not_in_state_actions_for_unpublished_version(self):
        version = factories.PollVersionFactory(state=constants.UNPUBLISHED)
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == 'PollContentVersion'][0]
        archive_url = reverse(
            'admin:djangocms_versioning_pollcontentversion_archive',
            args=(version.pk,))

        state_actions = admin.site._registry[version_model_proxy].state_actions(version)

        self.assertNotIn(archive_url, state_actions)

    def test_publish_in_state_actions_for_draft_version(self):
        version = factories.PollVersionFactory(state=constants.DRAFT)
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == 'PollContentVersion'][0]
        publish_url = reverse(
            'admin:djangocms_versioning_pollcontentversion_publish',
            args=(version.pk,))

        state_actions = admin.site._registry[version_model_proxy].state_actions(version)

        self.assertIn(publish_url, state_actions)

    def test_publish_not_in_state_actions_for_archived_version(self):
        version = factories.PollVersionFactory(state=constants.ARCHIVED)
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == 'PollContentVersion'][0]
        publish_url = reverse(
            'admin:djangocms_versioning_pollcontentversion_publish',
            args=(version.pk,))

        state_actions = admin.site._registry[version_model_proxy].state_actions(version)

        self.assertNotIn(publish_url, state_actions)

    def test_publish_not_in_state_actions_for_published_version(self):
        version = factories.PollVersionFactory(state=constants.PUBLISHED)
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == 'PollContentVersion'][0]
        publish_url = reverse(
            'admin:djangocms_versioning_pollcontentversion_publish',
            args=(version.pk,))

        state_actions = admin.site._registry[version_model_proxy].state_actions(version)

        self.assertNotIn(publish_url, state_actions)

    def test_publish_not_in_state_actions_for_unpublished_version(self):
        version = factories.PollVersionFactory(state=constants.UNPUBLISHED)
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == 'PollContentVersion'][0]
        publish_url = reverse(
            'admin:djangocms_versioning_pollcontentversion_publish',
            args=(version.pk,))

        state_actions = admin.site._registry[version_model_proxy].state_actions(version)

        self.assertNotIn(publish_url, state_actions)

    def test_edit_in_state_actions_for_draft_version(self):
        version = factories.PollVersionFactory(state=constants.DRAFT)
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == 'PollContentVersion'][0]
        edit_url = reverse(
            'admin:djangocms_versioning_pollcontentversion_edit_redirect',
            args=(version.pk,))

        state_actions = admin.site._registry[version_model_proxy].state_actions(version)

        self.assertIn(edit_url, state_actions)

    def test_edit_not_in_state_actions_for_archived_version(self):
        version = factories.PollVersionFactory(state=constants.ARCHIVED)
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == 'PollContentVersion'][0]
        edit_url = reverse(
            'admin:djangocms_versioning_pollcontentversion_edit_redirect',
            args=(version.pk,))

        state_actions = admin.site._registry[version_model_proxy].state_actions(version)

        self.assertNotIn(edit_url, state_actions)

    def test_edit_in_state_actions_for_published_version(self):
        version = factories.PollVersionFactory(state=constants.PUBLISHED)
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == 'PollContentVersion'][0]
        edit_url = reverse(
            'admin:djangocms_versioning_pollcontentversion_edit_redirect',
            args=(version.pk,))

        state_actions = admin.site._registry[version_model_proxy].state_actions(version)

        self.assertIn(edit_url, state_actions)

    def test_edit_not_in_state_actions_for_published_version_when_draft_exists(self):
        version = factories.PollVersionFactory(state=constants.PUBLISHED)
        factories.PollVersionFactory(
            state=constants.DRAFT, content__poll=version.content.poll)
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == 'PollContentVersion'][0]
        edit_url = reverse(
            'admin:djangocms_versioning_pollcontentversion_edit_redirect',
            args=(version.pk,))

        state_actions = admin.site._registry[version_model_proxy].state_actions(version)

        self.assertNotIn(edit_url, state_actions)

    def test_edit_not_in_state_actions_for_unpublished_version(self):
        version = factories.PollVersionFactory(state=constants.UNPUBLISHED)
        # Get the version model proxy from the main admin site
        # Trying to test this on the plain Version model throws exceptions
        version_model_proxy = [
            i for i in admin.site._registry if i.__name__ == 'PollContentVersion'][0]
        edit_url = reverse(
            'admin:djangocms_versioning_pollcontentversion_edit_redirect',
            args=(version.pk,))

        state_actions = admin.site._registry[version_model_proxy].state_actions(version)

        self.assertNotIn(edit_url, state_actions)


class VersionAdminViewTestCase(CMSTestCase):

    def setUp(self):
        self.superuser = self.get_superuser()
        self.versionable = PollsCMSConfig.versioning[0]

    def test_version_adding_is_disabled(self):
        with self.login_user_context(self.superuser):
            response = self.client.get(self.get_admin_url(self.versionable.version_model_proxy, 'add'))
        self.assertEqual(response.status_code, 403)

    def test_version_editing_is_disabled(self):
        version = factories.PollVersionFactory(content__text='test5')
        with self.login_user_context(self.superuser):
            response = self.client.get(self.get_admin_url(self.versionable.version_model_proxy, 'change', version.pk))
        self.assertEqual(response.status_code, 403)

    def test_version_deleting_is_disabled(self):
        with self.login_user_context(self.superuser):
            response = self.client.get(self.get_admin_url(self.versionable.version_model_proxy, 'delete', 1))
        self.assertEqual(response.status_code, 403)

    def test_grouper_view_requires_staff_permissions(self):
        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.get(self.get_admin_url(self.versionable.version_model_proxy, 'grouper'))
        self.assertEqual(response.status_code, 200)

    def test_grouper_view_requires_staff_permissions_(self):
        url = self.get_admin_url(self.versionable.version_model_proxy, 'grouper')
        with self.login_user_context(self.get_standard_user()):
            response = self.client.get(url)

        self.assertRedirects(response, admin_reverse('login') + '?next=' + url)


class ArchiveViewTestCase(CMSTestCase):

    def setUp(self):
        self.versionable = PollsCMSConfig.versioning[0]

    def test_archive_view_doesnt_allow_user_without_staff_permissions(self):
        poll_version = factories.PollVersionFactory(state=constants.DRAFT)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, 'archive', poll_version.pk)
        with self.login_user_context(self.get_standard_user()):
            response = self.client.post(url)

        self.assertRedirects(response, admin_reverse('login') + '?next=' + url)
        # status hasn't changed
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.DRAFT)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    @freeze_time(None)
    @patch('django.contrib.messages.success')
    def test_archive_view_sets_state_and_redirects(self, mocked_messages):
        poll_version = factories.PollVersionFactory(state=constants.DRAFT)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, 'archive', poll_version.pk)
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
        self.assertEqual(
            mocked_messages.call_args[0][1], "Version archived")
        # Redirect happened
        redirect_url = (self.get_admin_url(
            self.versionable.version_model_proxy, 'changelist')
            + '?grouper=' + str(poll_version_.content.poll.pk))
        self.assertRedirects(response, redirect_url, target_status_code=302)

    def test_archive_view_cannot_be_accessed_for_archived_version(self):
        poll_version = factories.PollVersionFactory(state=constants.ARCHIVED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, 'archive', poll_version.pk)

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertEqual(response.status_code, 404)
        # status hasn't changed
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.ARCHIVED)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    def test_archive_view_cannot_be_accessed_for_published_version(self):
        poll_version = factories.PollVersionFactory(state=constants.PUBLISHED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, 'archive', poll_version.pk)

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertEqual(response.status_code, 404)
        # status hasn't changed
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.PUBLISHED)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    def test_archive_view_cannot_be_accessed_for_unpublished_version(self):
        poll_version = factories.PollVersionFactory(state=constants.UNPUBLISHED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, 'archive', poll_version.pk)

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertEqual(response.status_code, 404)
        # status hasn't changed
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.UNPUBLISHED)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    @patch('django.contrib.messages.add_message')
    def test_archive_view_redirects_when_nonexistent_version(self, mocked_messages):
        url = self.get_admin_url(
            self.versionable.version_model_proxy, 'archive', 89)

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertRedirects(response, '/en/admin/', target_status_code=302)
        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], 30)  # warning level
        self.assertEqual(
            mocked_messages.call_args[0][2],
            'poll content version with ID "89" doesn\'t exist. Perhaps it was deleted?')

    @skip("Awaiting frontend work before this can be fixed")
    def test_archive_view_cant_be_accessed_by_get_request(self):
        poll_version = factories.PollVersionFactory(state=constants.DRAFT)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, 'archive', poll_version.pk)

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)


class PublishViewTestCase(CMSTestCase):

    def setUp(self):
        self.versionable = PollsCMSConfig.versioning[0]

    def test_publish_view_doesnt_allow_user_without_staff_permissions(self):
        poll_version = factories.PollVersionFactory(state=constants.DRAFT)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, 'publish', poll_version.pk)
        with self.login_user_context(self.get_standard_user()):
            response = self.client.post(url)

        self.assertRedirects(response, admin_reverse('login') + '?next=' + url)
        # status hasn't changed
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.DRAFT)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    @freeze_time(None)
    @patch('django.contrib.messages.success')
    def test_publish_view_sets_state_and_redirects(self, mocked_messages):
        poll_version = factories.PollVersionFactory(state=constants.DRAFT)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, 'publish', poll_version.pk)
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
        self.assertEqual(
            mocked_messages.call_args[0][1], "Version published")
        # Redirect happened
        redirect_url = (self.get_admin_url(
            self.versionable.version_model_proxy, 'changelist')
            + '?grouper=' + str(poll_version_.content.poll.pk))
        self.assertRedirects(response, redirect_url, target_status_code=302)

    def test_publish_view_cannot_be_accessed_for_archived_version(self):
        poll_version = factories.PollVersionFactory(state=constants.ARCHIVED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, 'publish', poll_version.pk)

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertEqual(response.status_code, 404)
        # status hasn't changed
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.ARCHIVED)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    def test_publish_view_cannot_be_accessed_for_published_version(self):
        poll_version = factories.PollVersionFactory(state=constants.PUBLISHED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, 'publish', poll_version.pk)

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertEqual(response.status_code, 404)
        # status hasn't changed
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.PUBLISHED)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    def test_publish_view_cannot_be_accessed_for_unpublished_version(self):
        poll_version = factories.PollVersionFactory(state=constants.UNPUBLISHED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, 'publish', poll_version.pk)

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertEqual(response.status_code, 404)
        # status hasn't changed
        poll_version_ = Version.objects.get(pk=poll_version.pk)
        self.assertEqual(poll_version_.state, constants.UNPUBLISHED)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)

    @patch('django.contrib.messages.add_message')
    def test_publish_view_redirects_when_nonexistent_version(self, mocked_messages):
        url = self.get_admin_url(
            self.versionable.version_model_proxy, 'publish', 89)

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertRedirects(response, '/en/admin/', target_status_code=302)
        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], 30)  # warning level
        self.assertEqual(
            mocked_messages.call_args[0][2],
            'poll content version with ID "89" doesn\'t exist. Perhaps it was deleted?')

    @skip("Awaiting frontend work before this can be fixed")
    def test_publish_view_cant_be_accessed_by_get_request(self):
        poll_version = factories.PollVersionFactory(state=constants.DRAFT)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, 'publish', poll_version.pk)

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
        # no status change has been tracked
        self.assertEqual(StateTracking.objects.all().count(), 0)



class EditRedirectTestCase(CMSTestCase):

    def setUp(self):
        self.versionable = PollsCMSConfig.versioning[0]

    def test_edit_redirect_view_doesnt_allow_user_without_staff_permissions(self):
        poll_version = factories.PollVersionFactory(state=constants.PUBLISHED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, 'edit_redirect', poll_version.pk)
        with self.login_user_context(self.get_standard_user()):
            response = self.client.post(url)

        self.assertRedirects(response, admin_reverse('login') + '?next=' + url)
        # no draft was created
        self.assertFalse(Version.objects.filter(state=constants.DRAFT).exists())

    @freeze_time(None)
    def test_edit_redirect_view_creates_draft_and_redirects(self):
        """If the version is published then create a draft and redirect
        to editing it.
        """
        published = factories.PollVersionFactory(state=constants.PUBLISHED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, 'edit_redirect', published.pk)
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
        redirect_url = (self.get_admin_url(
            PollContent, 'change', draft.content.pk))
        self.assertRedirects(response, redirect_url, target_status_code=302)

    def test_edit_redirect_view_doesnt_create_draft_if_draft_exists(self):
        """If the version is published, but there is a newer version
        that is a draft then redirect to editing the draft, don't create.
        """
        draft = factories.PollVersionFactory(state=constants.DRAFT)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, 'edit_redirect', draft.pk)
        user = self.get_staff_user_with_no_permissions()

        with self.login_user_context(user):
            response = self.client.post(url)

        # No drafts created
        self.assertFalse(Version.objects.exclude(pk=draft.pk).exists())
        # Redirect happened
        redirect_url = (self.get_admin_url(
            PollContent, 'change', draft.content.pk))
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
            self.versionable.version_model_proxy, 'edit_redirect', draft.pk)
        user = self.get_staff_user_with_no_permissions()

        with self.login_user_context(user):
            response = self.client.post(url)

        # Redirect happened
        redirect_url = (self.get_admin_url(
            PollContent, 'change', draft.content.pk))
        self.assertRedirects(response, redirect_url, target_status_code=302)

    def test_edit_redirect_view_cannot_be_accessed_for_archived_version(self):
        poll_version = factories.PollVersionFactory(state=constants.ARCHIVED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, 'edit_redirect', poll_version.pk)

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertEqual(response.status_code, 404)
        # no draft was created
        self.assertFalse(Version.objects.filter(state=constants.DRAFT).exists())

    def test_edit_redirect_view_cannot_be_accessed_for_unpublished_version(self):
        poll_version = factories.PollVersionFactory(state=constants.UNPUBLISHED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, 'edit_redirect', poll_version.pk)

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertEqual(response.status_code, 404)
        # no draft was created
        self.assertFalse(Version.objects.filter(state=constants.DRAFT).exists())

    def test_edit_redirect_view_cannot_be_accessed_for_published_version_when_draft_exists(self):
        published = factories.PollVersionFactory(state=constants.PUBLISHED)
        draft = factories.PollVersionFactory(
            state=constants.DRAFT, content__poll=published.content.poll)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, 'edit_redirect', published.pk)

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertEqual(response.status_code, 404)
        # no draft was created
        self.assertFalse(Version.objects.exclude(
            pk=draft.pk).filter(state=constants.DRAFT).exists())

    @patch('django.contrib.messages.add_message')
    def test_edit_redirect_view_handles_nonexistent_version(self, mocked_messages):
        url = self.get_admin_url(
            self.versionable.version_model_proxy, 'edit_redirect', 89)

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.post(url)

        self.assertRedirects(response, '/en/admin/', target_status_code=302)
        self.assertEqual(mocked_messages.call_count, 1)
        self.assertEqual(mocked_messages.call_args[0][1], 30)  # warning level
        self.assertEqual(
            mocked_messages.call_args[0][2],
            'poll content version with ID "89" doesn\'t exist. Perhaps it was deleted?')

    @skip("Awaiting frontend work before this can be fixed")
    def test_edit_redirect_view_cant_be_accessed_by_get_request(self):
        poll_version = factories.PollVersionFactory(state=constants.PUBLISHED)
        url = self.get_admin_url(
            self.versionable.version_model_proxy, 'edit_redirect', poll_version.pk)

        with self.login_user_context(self.get_staff_user_with_no_permissions()):
            response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
        # no draft was created
        self.assertFalse(Version.objects.filter(state=constants.DRAFT).exists())


class VersionChangeListTestCase(CMSTestCase):

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
                self.get_admin_url(self.versionable.version_model_proxy, 'changelist'),
                follow=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertIn('grouper', response.context['form'].fields)
        self.assertIn(
            (pv.content.poll.pk, str(pv.content.poll)),
            response.context['form'].fields['grouper'].choices,
        )

    def test_missing_grouper(self):
        """Test that going to a changelist with no grouper in querystring
        shows an error.
        """
        with self.login_user_context(self.superuser):
            response = self.client.get(
                self.get_admin_url(self.versionable.version_model_proxy, 'changelist') + '?foo=1',
                follow=True,
            )

        self.assertRedirects(response, '/en/admin/djangocms_versioning/pollcontentversion/?e=1')

    def test_grouper_filtering(self):
        pv = factories.PollVersionFactory()
        factories.PollVersionFactory.create_batch(4)

        with self.login_user_context(self.superuser):
            querystring = '?grouper={grouper}'.format(grouper=pv.content.poll_id)
            response = self.client.get(
                self.get_admin_url(self.versionable.version_model_proxy, 'changelist') + querystring,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn('cl', response.context)
        self.assertQuerysetEqual(
            response.context['cl'].queryset,
            [pv.pk],
            transform=lambda x: x.pk,
            ordered=False
        )
