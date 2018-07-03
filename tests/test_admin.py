from django.contrib import admin

from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.admin import (
    replace_admin_for_model,
    replace_admin_for_models,
    versioning_admin_factory,
    VersioningAdminMixin,
)
from djangocms_versioning.test_utils.polls.models import Poll


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
        """Test that calling `replace_admin_for_model` on a model that
        isn't registered in admin is a no-op.
        """
        replace_admin_for_model(self.model, self.site)

        self.assertNotIn(self.model, self.site._registry)

    def test_replace_admin_on_registered_model(self):
        self.site.register(self.model, self.admin_class)

        replace_admin_for_model(self.model, self.site)

        self.assertIn(self.model, self.site._registry)
        self.assertIn(self.admin_class, self.site._registry[self.model].__class__.mro())
        self.assertIn(VersioningAdminMixin, self.site._registry[self.model].__class__.mro())

    def test_replace_models(self):
        self.site.register(self.model, self.admin_class)

        replace_admin_for_models([self.model], self.site)

        self.assertIn(self.model, self.site._registry)
        self.assertIn(self.admin_class, self.site._registry[self.model].__class__.mro())
        self.assertIn(VersioningAdminMixin, self.site._registry[self.model].__class__.mro())
