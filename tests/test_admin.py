from django.contrib import admin

from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.admin import (
    replace_admin_for_model,
    versioning_admin_factory,
    VersioningAdminMixin,
)
from djangocms_versioning.test_utils.polls.models import Poll


class AdminVersioningTestCase(CMSTestCase):

    def test_admin_factory(self):
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

    def test_replace_admin_on_unregistered_model(self):
        replace_admin_for_model(self.model, self.site)

        self.assertFalse(len(self.site._registry))

    def test_replace_admin_on_registered_model(self):
        admin_class = type('TestAdmin', (admin.ModelAdmin, ), {})
        self.site.register(self.model, )

        replace_admin_for_model(self.model, self.site)

        self.assertTrue(self.model in self.site._registry)
        self.assertNotEqual(self.site._registry[self.model], admin_class)
