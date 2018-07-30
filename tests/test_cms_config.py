from unittest.mock import Mock

from django.apps import apps
from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured

from cms.app_registration import get_cms_config_apps, get_cms_extension_apps
from cms.test_utils.testcases import CMSTestCase
from cms.utils.setup import setup_cms_apps

from djangocms_versioning.admin import VersionAdmin, VersioningAdminMixin
from djangocms_versioning.cms_config import VersioningCMSExtension
from djangocms_versioning.test_utils.blogpost.cms_config import BlogpostCMSConfig
from djangocms_versioning.test_utils.blogpost.models import (
    BlogContent,
    BlogPost,
    CommentContent,
)
from djangocms_versioning.test_utils.polls.cms_config import PollsCMSConfig
from djangocms_versioning.test_utils.polls.models import Poll, PollContent
from djangocms_versioning.versionable import Versionable, VersionableList


class CMSConfigUnitTestCase(CMSTestCase):

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
            versioning=Versionable(grouper=Poll, content=PollContent)
        )
        with self.assertRaises(ImproperlyConfigured):
            extensions.handle_versioning_setting(cms_config)

    def test_raises_exception_if_not_versionable_class(self):
        """Tests ImproperlyConfigured exception is raised if elements
        in the versioning list are not instances of Versionable classes
        """
        extensions = VersioningCMSExtension()
        cms_config = Mock(spec=[],
                          djangocms_versioning_enabled=True,
                          versioning=['aaa', {}])
        with self.assertRaises(ImproperlyConfigured):
            extensions.handle_versioning_setting(cms_config)

    def test_versionables_list_created(self):
        """Test handle_versioning_setting method adds all the
        models into the versionables list
        """
        extension = VersioningCMSExtension()
        poll_versionable = Versionable(grouper=Poll, content=PollContent)
        blog_versionable = Versionable(grouper=BlogPost, content=BlogContent)
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
            versioning=VersionableList([Versionable(grouper=Poll, content=PollContent)]))
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

    def test_all_versionables_collected(self):
        """Check that all version models defined in cms_config.py
        are collected into a list
        """
        setup_cms_apps()  # discover and run all cms_config.py files
        app = apps.get_app_config('djangocms_versioning')
        poll_versionable = PollsCMSConfig.versioning[0]
        blog_versionable = BlogpostCMSConfig.versioning[0]
        comment_versionable = BlogpostCMSConfig.versioning[1]
        self.assertListEqual(
            app.cms_extension.versionables,
            [poll_versionable, blog_versionable, comment_versionable]
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
        # Check that CommentContent were not registered to the admin
        # (they are defined in cms_config.py but are not registered
        # to the admin)
        self.assertNotIn(CommentContent, admin.site._registry)
