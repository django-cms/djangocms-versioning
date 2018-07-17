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
        admin_site = admin.AdminSite()
        self.model_admin = admin_class(model=PollContent, admin_site=admin_site)

    def test_version_is_added_for_change_false(self):
        p1 = Poll.objects.create(name="p1")
        pc1 = PollContent.objects.create(text="blah", language="en", poll=p1)
        request = RequestFactory().get('/admin/polls/pollcontent/')
        self.model_admin.save_model(request, pc1, None, change=False)
        extension = apps.get_app_config('djangocms_versioning').cms_extension
        version_model_class = extension.content_to_version_models[PollContent]
        check_obj = version_model_class.objects.get(content_id=pc1)
        self.assertTrue(check_obj)

    def test_version_is_not_added_for_change_true(self):
        p2 = Poll.objects.create(name="p2")
        pc2 = PollContent.objects.create(text="no blah blah", language="en", poll=p2)
        request = RequestFactory().get('/admin/polls/pollcontent/')
        self.model_admin.save_model(request, pc2, None, change=True)
        extension = apps.get_app_config('djangocms_versioning').cms_extension
        version_model_class = extension.content_to_version_models[PollContent]
        check_obj_exist = version_model_class.objects.filter(content_id=pc2.id).exists()
        self.assertFalse(check_obj_exist)
