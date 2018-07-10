from mock import Mock

from django.apps import apps
from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured

from cms.app_registration import get_cms_extension_apps, get_cms_config_apps
from cms.test_utils.testcases import CMSTestCase
from cms.utils.setup import setup_cms_apps

from djangocms_versioning.admin import VersioningAdminMixin
from djangocms_versioning.cms_config import VersioningCMSExtension
from djangocms_versioning.test_utils.blogpost.models import (
    BlogPostVersion,
    BlogContent
)
from djangocms_versioning.test_utils.polls.models import PollVersion, PollContent


class CMSConfigUnitTestCase(CMSTestCase):

    def test_missing_cms_config_attribute(self):
        """
        Tests the if the  versioning_models attribute has been specified
        """
        extensions = VersioningCMSExtension()
        cms_config = Mock(spec=[],
                          djangocms_versioning_enabled=True)
        # versioning_models=[] is missing - should raise an exception
        with self.assertRaises(ImproperlyConfigured):
            extensions.handle_versioning_models_setting(cms_config)

    def test_get_version_model(self):
        extensions = VersioningCMSExtension()
        extensions._version_models = ['Test_version']
        self.assertListEqual(extensions.get_version_models(), ['Test_version'])

    def test_handle_versioning_models(self):
        extensions = VersioningCMSExtension()
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning_models=[PollVersion, BlogPostVersion]
        )
        extensions.handle_versioning_models_setting(cms_config)
        self.assertListEqual(
            extensions._version_models, [PollVersion, BlogPostVersion])

    def test_handle_admin_classes(self):
        extensions = VersioningCMSExtension()
        cms_config = Mock(
            spec=[], djangocms_versioning_enabled=True,
            versioning_models=[PollVersion])
        extensions.handle_admin_classes(cms_config)
        self.assertIn(PollContent, admin.site._registry)
        self.assertIn(
            VersioningAdminMixin,
            admin.site._registry[PollContent].__class__.mro()
        )


class VersioningIntegrationTestCase(CMSTestCase):

    def setUp(self):
        # The results of get_cms_extension_apps and get_cms_config_apps
        # are cached. Clear this cache because installed apps change
        # between tests and therefore unlike in a live environment,
        # results of this function can change between tests
        get_cms_extension_apps.cache_clear()
        get_cms_config_apps.cache_clear()

    def test_all_version_models_added(self):
        setup_cms_apps()
        app = apps.get_app_config('djangocms_versioning')
        versions_collected = app.cms_extension.get_version_models()
        self.assertListEqual(versions_collected, [PollVersion, BlogPostVersion])

    def test_admin_classes_reregistered(self):
        """Integration test that all content models that are registered
        with the admin have their admin class overridden with a
        subclass of VersioningAdminMixin
        """
        setup_cms_apps()
        self.assertIn(PollContent, admin.site._registry)
        self.assertIn(
            VersioningAdminMixin,
            admin.site._registry[PollContent].__class__.mro()
        )
        self.assertIn(BlogContent, admin.site._registry)
        self.assertIn(
            VersioningAdminMixin,
            admin.site._registry[BlogContent].__class__.mro()
        )
        # TODO: case when not registered with admin
