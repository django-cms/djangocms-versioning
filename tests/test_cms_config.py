from unittest.mock import Mock, patch

from django.apps import apps
from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured

from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.admin import VersionAdmin, VersioningAdminMixin
from djangocms_versioning.cms_config import (
    VersioningCMSConfig,
    VersioningCMSExtension,
)
from djangocms_versioning.datastructures import VersionableItem, default_copy
from djangocms_versioning.models import Version
from djangocms_versioning.test_utils.blogpost.cms_config import (
    BlogpostCMSConfig,
)
from djangocms_versioning.test_utils.blogpost.models import (
    BlogContent,
    Comment,
)
from djangocms_versioning.test_utils.polls.cms_config import PollsCMSConfig
from djangocms_versioning.test_utils.polls.models import Poll, PollContent


class VersioningExtensionUnitTestCase(CMSTestCase):

    def test_missing_cms_config_attribute(self):
        """
        Tests, if the versioning attribute has not been specified,
        an ImproperlyConfigured exception is raised
        """
        extensions = VersioningCMSExtension()
        cms_config = Mock(spec=[],
                          djangocms_versioning_enabled=True)
        with self.assertRaises(ImproperlyConfigured):
            extensions.handle_versioning_setting(cms_config)

    def test_raises_exception_if_versioning_not_iterable(self):
        """Tests ImproperlyConfigured exception is raised if
        versioning setting is not an iterable
        """
        extensions = VersioningCMSExtension()
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning=VersionableItem(
                content_model=PollContent, grouper_field_name='poll',
                copy_function=default_copy)
        )
        with self.assertRaises(ImproperlyConfigured):
            extensions.handle_versioning_setting(cms_config)

    def test_raises_exception_if_not_versionable_class(self):
        """Tests ImproperlyConfigured exception is raised if elements
        in the versioning list are not instances of VersionableItem classes
        """
        extensions = VersioningCMSExtension()
        cms_config = Mock(spec=[],
                          djangocms_versioning_enabled=True,
                          versioning=['aaa', {}])
        with self.assertRaises(ImproperlyConfigured):
            extensions.handle_versioning_setting(cms_config)

    def test_raises_exception_if_content_class_already_registered(self):
        """Tests ImproperlyConfigured exception is raised if the same
        content class is registered twice
        """
        extension = VersioningCMSExtension()
        poll_versionable = VersionableItem(
            content_model=PollContent, grouper_field_name='poll',
            copy_function=default_copy)
        poll_versionable2 = VersionableItem(
            content_model=PollContent, grouper_field_name='poll',
            copy_function=default_copy)
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning=[poll_versionable, poll_versionable2]
        )
        with self.assertRaises(ImproperlyConfigured):
            extension.handle_versioning_setting(cms_config)

    def test_versionables_list_created(self):
        """Test handle_versioning_setting method adds all the
        models into the versionables list
        """
        extension = VersioningCMSExtension()
        poll_versionable = VersionableItem(
            content_model=PollContent, grouper_field_name='poll',
            copy_function=default_copy)
        blog_versionable = VersionableItem(
            content_model=BlogContent, grouper_field_name='blogpost',
            copy_function=default_copy)
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning=[poll_versionable, blog_versionable]
        )
        extension.handle_versioning_setting(cms_config)
        self.assertListEqual(
            extension.versionables, [poll_versionable, blog_versionable])

    def test_handle_content_admin_classes(self):
        """Test handle_admin_classes replaces the admin model class
        with an admin model class that inherits from VersioningAdminMixin
        """
        extensions = VersioningCMSExtension()
        cms_config = Mock(
            spec=[], djangocms_versioning_enabled=True,
            versioning=[VersionableItem(
                content_model=PollContent, grouper_field_name='poll',
                copy_function=default_copy
            )])
        extensions.handle_admin_classes(cms_config)
        self.assertIn(PollContent, admin.site._registry)
        self.assertIn(
            VersioningAdminMixin,
            admin.site._registry[PollContent].__class__.mro()
        )

    def test_is_content_model_versioned(self):
        """Test that is_content_model_versioned returns True for
        content model that's versioned
        """
        extension = VersioningCMSExtension()
        extension.versionables = [VersionableItem(
            content_model=PollContent, grouper_field_name='poll',
            copy_function=default_copy
        )]

        self.assertTrue(extension.is_content_model_versioned(PollContent))

    def test_is_content_model_not_versioned(self):
        """Test that is_content_model_versioned returns False for
        content model that's not versioned
        """
        extension = VersioningCMSExtension()
        extension.versionables = []

        self.assertFalse(extension.is_content_model_versioned(PollContent))

    def test_handle_version_admin(self):
        versionable = Mock(
            spec=[], djangocms_versioning_enabled=True, content_model=PollContent,
            grouper_model=Poll,
            version_model_proxy=apps.get_model('djangocms_versioning', 'PollContentVersion')
        )

        with patch.object(versionable, 'version_model_proxy'):
            extensions = VersioningCMSExtension()
            cms_config = Mock(
                spec=[], djangocms_versioning_enabled=True,
                versioning=[versionable])
            extensions.handle_version_admin(cms_config)
        self.assertIn(versionable.version_model_proxy, admin.site._registry)
        self.assertIn(
            VersionAdmin,
            admin.site._registry[versionable.version_model_proxy].__class__.mro()
        )


# NOTE: These tests simply test what has already happened on start up
# when the app registry has been instantiated.
class VersioningIntegrationTestCase(CMSTestCase):

    def test_all_versionables_collected(self):
        """Check that all version models defined in cms_config.py
        are collected into a list
        """
        app = apps.get_app_config('djangocms_versioning')
        page_versionable = VersioningCMSConfig.versioning[0]
        poll_versionable = PollsCMSConfig.versioning[0]
        blog_versionable = BlogpostCMSConfig.versioning[0]
        comment_versionable = BlogpostCMSConfig.versioning[1]
        self.assertListEqual(
            app.cms_extension.versionables,
            [page_versionable, poll_versionable, blog_versionable, comment_versionable]
        )

    def test_admin_classes_reregistered(self):
        """Integration test that all content models that are registered
        with the admin have their admin class overridden with a
        subclass of VersioningAdminMixin
        """
        # TODO: Awaiting FIL-313 to land on core
        # Check PageContent has had its admin class modified
        # self.assertIn(PageContent, admin.site._registry)
        # self.assertIn(
        #     VersioningAdminMixin,
        #     admin.site._registry[PageContent].__class__.mro()
        # )
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

    def test_version_admin_registered(self):
        """Integration test that for each content model
        there's a version proxy registered with the admin
        subclassing VersionAdmin
        """
        version_proxies = [
            model for model in admin.site._registry if issubclass(model, Version)
        ]
        source_models_in_proxies = [model._source_model for model in version_proxies]
        source_model_to_proxy = dict(zip(source_models_in_proxies, version_proxies))

        self.assertIn(PollContent, source_models_in_proxies)
        self.assertIn(
            VersionAdmin,
            admin.site._registry[source_model_to_proxy[PollContent]].__class__.mro()
        )

        self.assertIn(BlogContent, source_models_in_proxies)
        self.assertIn(
            VersionAdmin,
            admin.site._registry[source_model_to_proxy[BlogContent]].__class__.mro()
        )

        self.assertNotIn(Comment, source_models_in_proxies)
