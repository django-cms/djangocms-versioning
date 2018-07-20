import datetime
from unittest.mock import patch

from django.apps import apps
from django.contrib import admin
from django.test import RequestFactory

from cms.test_utils.testcases import CMSTestCase

import pytz
from freezegun import freeze_time

import djangocms_versioning.helpers
from djangocms_versioning.admin import VersionAdmin, VersioningAdminMixin
from djangocms_versioning.helpers import (
    register_version_admin_for_models,
    replace_admin_for_models,
    versioning_admin_factory,
)
from djangocms_versioning.test_utils import factories
from djangocms_versioning.test_utils.blogpost.models import (
    BlogContent,
    BlogPost,
)
from djangocms_versioning.test_utils.polls.models import (
    Answer,
    Poll,
    PollContent,
    PollVersion,
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

    def setUp(self):
        admin_class = type(
             'PollModelAdmin', (VersioningAdminMixin, admin.ModelAdmin), {})
        admin_site = admin.AdminSite()
        self.model_admin = admin_class(model=PollContent, admin_site=admin_site)

    def test_poll_version_is_added_for_change_false(self):
        with freeze_time('2011-01-06'):
            p1 = Poll.objects.create(name="p1")
            pc1 = PollContent.objects.create(text="blah", language="en", poll=p1)
            request = RequestFactory().get('/admin/polls/pollcontent/')
            self.model_admin.save_model(request, pc1, None, change=False)
            check_obj = PollVersion.objects.get(content_id=pc1)
            self.assertTrue(check_obj)
            self.assertEqual(check_obj.created, datetime.datetime(2011, 1, 6, tzinfo=pytz.utc))
            self.assertEqual(check_obj.label, "")
            self.assertEqual(check_obj.start, None)
            self.assertEqual(check_obj.end, None)
            self.assertEqual(check_obj.is_active, True)

    def test_poll_version_is_not_added_for_change_true(self):
        p2 = Poll.objects.create(name="p2")
        pc2 = PollContent.objects.create(text="no blah blah", language="en", poll=p2)
        request = RequestFactory().get('/admin/polls/pollcontent/')
        self.model_admin.save_model(request, pc2, None, change=True)
        extension = apps.get_app_config('djangocms_versioning').cms_extension
        version_model_class = extension.content_to_version_models[PollContent]
        check_obj_exist = version_model_class.objects.filter(content_id=pc2.id).exists()
        self.assertFalse(check_obj_exist)

    def test_blogpost_version_is_added_for_change_false(self):
        b1 = BlogPost.objects.create(name="b1")
        bc1 = BlogContent.objects.create(text="blah", language="en", blogpost=b1)
        request = RequestFactory().get('/admin/blogposts/blogcontent/')
        self.model_admin.save_model(request, bc1, None, change=False)
        extension = apps.get_app_config('djangocms_versioning').cms_extension
        version_model_class = extension.content_to_version_models[BlogContent]
        check_obj = version_model_class.objects.get(content_id=bc1)
        self.assertTrue(check_obj)

    def test_blogpost_version_is_not_added_for_change_true(self):
        b2 = BlogPost.objects.create(name="b2")
        bc2 = BlogContent.objects.create(text="no blah blah", language="en", blogpost=b2)
        request = RequestFactory().get('/admin/blogposts/blogcontent/')
        self.model_admin.save_model(request, bc2, None, change=True)
        extension = apps.get_app_config('djangocms_versioning').cms_extension
        version_model_class = extension.content_to_version_models[BlogContent]
        check_obj_exist = version_model_class.objects.filter(content_id=bc2.id).exists()
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

    def setUp(self):
        self.model = PollVersion
        self.site = admin.AdminSite()

    def test_register_version_admin(self):
        """Test that calling register_version_admin_for_models registers
        VersionAdmin for specified models.
        """
        register_version_admin_for_models([self.model], self.site)

        self.assertIn(self.model, self.site._registry)
        self.assertEqual(self.site._registry[self.model].__class__, VersionAdmin)

    def test_register_version_admin_again(self):
        """Test that, if a version model's admin class is already registered,
        nothing happens when calling register_version_admin_for_models
        for that model.
        """
        register_version_admin_for_models([self.model], self.site)

        with patch.object(self.site, 'register') as mock:
            register_version_admin_for_models([self.model], self.site)

        mock.assert_not_called()


class VersionAdminTestCase(CMSTestCase):

    def setUp(self):
        self.model = PollVersion
        self.site = admin.AdminSite()
        register_version_admin_for_models([self.model], self.site)
        self.superuser = self.get_superuser()

    def test_admin_queryset_num_queries(self):
        """Test that accessing Version.content in changelist
        doesn't result in additional query
        """
        self.assertIn(
            'content',
            self.site._registry[PollVersion].list_select_related,
        )

    def test_content_link(self):
        version = factories.PollContentWithVersionFactory(text='test4').pollversion
        self.assertEqual(
            self.site._registry[PollVersion].content_link(version),
            '<a href="{url}">{label}</a>'.format(
                url='/en/admin/polls/pollcontent/1/change/',
                label='test4',
            ),
        )

    def test_version_adding_is_disabled(self):
        with self.login_user_context(self.superuser):
            response = self.client.get(self.get_admin_url(self.model, 'add'))
        self.assertEqual(response.status_code, 403)

    def test_version_editing_is_disabled(self):
        version = factories.PollContentWithVersionFactory().pollversion
        with self.login_user_context(self.superuser):
            response = self.client.get(self.get_admin_url(self.model, 'change', version.pk))
        self.assertEqual(response.status_code, 403)

    def test_version_deleting_is_disabled(self):
        with self.login_user_context(self.superuser):
            response = self.client.get(self.get_admin_url(self.model, 'delete', 1))
        self.assertEqual(response.status_code, 403)

    def test_version_deleting_is_disabled(self):
        with self.login_user_context(self.superuser):
            response = self.client.get(self.get_admin_url(self.model, 'delete', 1))
        self.assertEqual(response.status_code, 403)
