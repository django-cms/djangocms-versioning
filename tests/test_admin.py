from unittest.mock import patch

from django.apps import apps
from django.contrib import admin
from django.test import RequestFactory

from cms.test_utils.testcases import CMSTestCase

import djangocms_versioning.helpers
from djangocms_versioning.admin import VersioningAdminMixin
from djangocms_versioning.helpers import (
    replace_admin_for_models,
    versioning_admin_factory,
)
from djangocms_versioning.test_utils.polls.models import Answer, Poll, PollContent


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
        # admin_class = versioning_admin_factory(PollModelAdmin)
        admin_site = admin.AdminSite()
        self.model_admin = admin_class(model=PollContent, admin_site=admin_site)

    def test_only_fetches_latest_content_records(self):


        #PollModelAdmin()
        p1 = Poll()
        p1.name = "p1"
        p1.save()
        pc1 = PollContent()
        pc1.text = "blah"
        pc1.language = "en"
        pc1.poll = p1
        pc1.save()

        request = RequestFactory().get('/admin/polls/pollcontent/')
        self.model_admin.save_model(request, pc1, None, change=False)

        extension = apps.get_app_config('djangocms_versioning').cms_extension
        version_model_class = extension.content_to_version_models[PollContent]
        print(version_model_class)
        # get the version model with poll_id
        # check if record exists or not


        # p1.text = "Hello Poll"

    #     poll = factories.PollFactory()
    #     # Make sure django sets the created date far in the past
    #     with freeze_time('2014-01-01'):
    #         factories.PollContentFactory.create_batch(
    #             4, poll=poll)
    #     # For this one the created date will be now
    #     poll_content = factories.PollContentFactory(poll=poll)
    #     request = RequestFactory().get('/admin/polls/pollcontent/')
    #
    #     admin_queryset = self.model_admin.get_queryset(request)
    #
    #     self.assertQuerysetEqual(
    #         admin_queryset, [poll_content.pk], transform=lambda x: x.pk)
