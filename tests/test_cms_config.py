from mock import Mock

from django.apps import apps
from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured

from cms.app_registration import get_cms_config_apps, get_cms_extension_apps
from cms.test_utils.testcases import CMSTestCase
from cms.utils.setup import setup_cms_apps

from djangocms_versioning.admin import VersioningAdminMixin
from djangocms_versioning.cms_config import VersioningCMSExtension
from djangocms_versioning.test_utils.blogpost.models import (
    BlogContent,
    BlogPostVersion,
    Comment,
    CommentVersion,
)
from djangocms_versioning.test_utils.polls.models import (
    PollContent,
    PollVersion,
)


class CMSConfigUnitTestCase(CMSTestCase):

    def test_missing_cms_config_attribute(self):
        """
        Tests, if the versioning_models attribute has not been specified,
        an ImproperlyConfigured exception is raised
        """
        extensions = VersioningCMSExtension()
        cms_config = Mock(spec=[],
                          djangocms_versioning_enabled=True)
        with self.assertRaises(ImproperlyConfigured):
            extensions.handle_versioning_models_setting(cms_config)

    def test_raises_exception_if_versioning_models_not_iterable(self):
        """Tests ImproperlyConfigured exception is raised if
        versioning_models setting is not an iterable
        """
        extensions = VersioningCMSExtension()
        cms_config = Mock(spec=[],
                          djangocms_versioning_enabled=True,
                          versioning_models=PollVersion)
        with self.assertRaises(ImproperlyConfigured):
            extensions.handle_versioning_models_setting(cms_config)

    def test_raises_exception_if_not_a_class(self):
        """Tests ImproperlyConfigured exception is raised if elements
        in the versioning_models list are not classes
        """
        extensions = VersioningCMSExtension()
        cms_config = Mock(spec=[],
                          djangocms_versioning_enabled=True,
                          versioning_models=['aaa', {}])
        with self.assertRaises(ImproperlyConfigured):
            extensions.handle_versioning_models_setting(cms_config)

    def test_raises_exception_if_doesnt_inherit_from_base_version(self):
        """Tests ImproperlyConfigured exception is raised if elements
        in the versioning_models list do not inherit from BaseVersion
        """
        extensions = VersioningCMSExtension()
        cms_config = Mock(spec=[],
                          djangocms_versioning_enabled=True,
                          versioning_models=[PollContent])
        with self.assertRaises(ImproperlyConfigured):
            extensions.handle_versioning_models_setting(cms_config)

    def test_versioning_models_list_created(self):
        """Test handle_versioning_models_setting method adds all the
        models into the _versioning_models list
        """
        extensions = VersioningCMSExtension()
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning_models=[PollVersion, BlogPostVersion]
        )
        extensions.handle_versioning_models_setting(cms_config)
        self.assertListEqual(
            extensions.version_models, [PollVersion, BlogPostVersion])

    def test_content_to_version_model_dict_created(self):
        """Test handle_versioning_models_setting method creates a
        dictionary which tells us what the versioning model is for each
        registered content model
        """
        extensions = VersioningCMSExtension()
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning_models=[PollVersion, BlogPostVersion]
        )
        extensions.handle_versioning_models_setting(cms_config)
        self.assertDictEqual(
            extensions.content_to_version_models,
            {PollContent: PollVersion, BlogContent: BlogPostVersion})

    def test_handle_admin_classes(self):
        """Test handle_admin_classes replaces the admin model class
        with an admin model class that inherits from VersioningAdminMixin
        """
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
        """Check that all version models defined in cms_config.py
        are collected into a list
        """
        setup_cms_apps()  # discover and run all cms_config.py files
        app = apps.get_app_config('djangocms_versioning')
        versions_collected = app.cms_extension.version_models
        self.assertListEqual(
            versions_collected,
            [PollVersion, BlogPostVersion, CommentVersion]
        )

    def test_content_to_version_dict_created(self):
        """Check that we create a dictionary which tells us what
        the versioning model is for each registered content model
        """
        setup_cms_apps()  # discover and run all cms_config.py files
        app = apps.get_app_config('djangocms_versioning')
        self.assertDictEqual(
            app.cms_extension.content_to_version_models,
            {
                PollContent: PollVersion,
                BlogContent: BlogPostVersion,
                Comment: CommentVersion
            }
        )

    def test_admin_classes_reregistered(self):
        """Integration test that all content models that are registered
        with the admin have their admin class overridden with a
        subclass of VersioningAdminMixin
        """
        setup_cms_apps()  # discover and run all cms_config.py files
        # Check PollContent has had its admin class modified
        self.assertIn(PollContent, admin.site._registry)
        self.assertIn(
            VersioningAdminMixin,
            admin.site._registry[PollContent].__class__.mro()
        )
        # Check BlogContent has had its admin class modified
        self.assertIn(BlogContent, admin.site._registry)
        self.assertIn(
            VersioningAdminMixin,
            admin.site._registry[BlogContent].__class__.mro()
        )
        # Check that Comments were not registered to the admin
        # (they are defined in cms_config.py but are not registered
        # to the admin)
        self.assertNotIn(Comment, admin.site._registry)
