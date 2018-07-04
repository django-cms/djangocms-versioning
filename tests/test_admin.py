from django.contrib import admin

from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.admin import (
    _replace_admin_for_model,
    replace_admin_for_models,
    versioning_admin_factory,
    VersioningAdminMixin,
)
from djangocms_versioning.test_utils.polls.models import Answer, Poll


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
        """Test that calling `_replace_admin_for_model` on a model that
        isn't registered in admin is a no-op.
        """
        _replace_admin_for_model(self.model, self.site)

        self.assertNotIn(self.model, self.site._registry)

    def test_replace_admin_on_registered_models(self):
        self.site.register(self.model, self.admin_class)
        self.site.register(Answer, self.admin_class)
        models = [self.model, Answer]

        replace_admin_for_models(models, self.site)

        for model in models:
            self.assertIn(model, self.site._registry)
            self.assertIn(self.admin_class, self.site._registry[model].__class__.mro())
            self.assertIn(VersioningAdminMixin, self.site._registry[model].__class__.mro())
