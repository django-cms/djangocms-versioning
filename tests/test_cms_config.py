from unittest.mock import Mock

from django.apps import apps
from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured

from cms.app_registration import get_cms_config_apps, get_cms_extension_apps
from cms.test_utils.testcases import CMSTestCase
from cms.utils.setup import setup_cms_apps

from djangocms_versioning.admin import VersioningAdminMixin
from djangocms_versioning.cms_config import VersioningCMSExtension
from djangocms_versioning.datastructures import VersionableItem
from djangocms_versioning.test_utils.blogpost.cms_config import (
    BlogpostCMSConfig,
)
from djangocms_versioning.test_utils.blogpost.models import (
    BlogContent,
    Comment,
)
from djangocms_versioning.test_utils.polls.cms_config import PollsCMSConfig
from djangocms_versioning.test_utils.polls.models import PollContent
from djangocms_versioning.test_utils.relationships import models as relationship_models


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
            versioning=VersionableItem(content_model=PollContent, grouper_field_name='poll')
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

    def test_versionables_list_created(self):
        """Test handle_versioning_setting method adds all the
        models into the versionables list
        """
        extension = VersioningCMSExtension()
        poll_versionable = VersionableItem(
            content_model=PollContent, grouper_field_name='poll',
            copy_functions={'answer.poll_content': lambda old_value: old_value})
        blog_versionable = VersionableItem(
            content_model=BlogContent, grouper_field_name='blogpost')
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
            versioning=[VersionableItem(content_model=PollContent, grouper_field_name='poll')])
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
        extension.versionables = [VersionableItem(content_model=PollContent, grouper_field_name='poll')]

        self.assertTrue(extension.is_content_model_versioned(PollContent))

    def test_is_content_model_not_versioned(self):
        """Test that is_content_model_versioned returns False for
        content model that's not versioned
        """
        extension = VersioningCMSExtension()
        extension.versionables = []

        self.assertFalse(extension.is_content_model_versioned(PollContent))


class CMSConfigFKTestCase(CMSTestCase):
    """Tests for raising an ImproperlyConfigured error when copy
    functions for FKs aren't provided.
    """

    def test_one_to_one_fwd_rel_raises_exception_if_function_not_provided(self):
        extensions = VersioningCMSExtension()
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning=[
                VersionableItem(
                    content_model=relationship_models.Content1to1F,
                    grouper_field_name='grouper',
                )
            ]
        )
        with self.assertRaises(ImproperlyConfigured):
            extensions.handle_versioning_setting(cms_config)

    def test_one_to_one_fwd_rel_doesnt_raise_exception_if_function_provided(self):
        extensions = VersioningCMSExtension()
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning=[
                VersionableItem(
                    content_model=relationship_models.Content1to1F,
                    grouper_field_name='grouper',
                    copy_functions={
                        'rel': lambda old_value: old_value
                    }
                )
            ]
        )
        try:
            extensions.handle_versioning_setting(cms_config)
        except ImproperlyConfigured:
            self.fail("Unexpectedly raised ImproperlyConfigured")

    def test_one_to_one_bwd_rel_raises_exception_if_function_not_provided(self):
        extensions = VersioningCMSExtension()
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning=[
                VersionableItem(
                    content_model=relationship_models.Content1to1B,
                    grouper_field_name='grouper',
                )
            ]
        )
        with self.assertRaises(ImproperlyConfigured):
            extensions.handle_versioning_setting(cms_config)

    def test_one_to_one_bwd_rel_doesnt_raise_exception_if_function_provided(self):
        extensions = VersioningCMSExtension()
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning=[
                VersionableItem(
                    content_model=relationship_models.Content1to1B,
                    grouper_field_name='grouper',
                    copy_functions={
                        'onetooneb.rel': lambda old_value: old_value
                    }
                )
            ]
        )
        try:
            extensions.handle_versioning_setting(cms_config)
        except ImproperlyConfigured:
            self.fail("Unexpectedly raised ImproperlyConfigured")

    def test_one_to_many_fwd_rel_raises_exception_if_function_not_provided(self):
        extensions = VersioningCMSExtension()
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning=[
                VersionableItem(
                    content_model=relationship_models.Content1toManyF,
                    grouper_field_name='grouper',
                )
            ]
        )
        with self.assertRaises(ImproperlyConfigured):
            extensions.handle_versioning_setting(cms_config)

    def test_one_to_many_fwd_rel_doesnt_raise_exception_if_function_provided(self):
        extensions = VersioningCMSExtension()
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning=[
                VersionableItem(
                    content_model=relationship_models.Content1toManyF,
                    grouper_field_name='grouper',
                    copy_functions={
                        'rel': lambda old_value: old_value
                    }
                )
            ]
        )
        try:
            extensions.handle_versioning_setting(cms_config)
        except ImproperlyConfigured:
            self.fail("Unexpectedly raised ImproperlyConfigured")

    def test_one_to_many_bwd_rel_raises_exception_if_function_not_provided(self):
        extensions = VersioningCMSExtension()
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning=[
                VersionableItem(
                    content_model=relationship_models.Content1toManyB,
                    grouper_field_name='grouper',
                )
            ]
        )
        with self.assertRaises(ImproperlyConfigured):
            extensions.handle_versioning_setting(cms_config)

    def test_one_to_many_bwd_rel_doesnt_raise_exception_if_function_provided(self):
        extensions = VersioningCMSExtension()
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning=[
                VersionableItem(
                    content_model=relationship_models.Content1toManyB,
                    grouper_field_name='grouper',
                    copy_functions={
                        'onetomanyb.rel': lambda old_value: old_value
                    }
                )
            ]
        )
        try:
            extensions.handle_versioning_setting(cms_config)
        except ImproperlyConfigured:
            self.fail("Unexpectedly raised ImproperlyConfigured")

    def test_many_to_many_fwd_rel_raises_exception_if_function_not_provided(self):
        extensions = VersioningCMSExtension()
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning=[
                VersionableItem(
                    content_model=relationship_models.ContentManytoManyF,
                    grouper_field_name='grouper',
                )
            ]
        )
        with self.assertRaises(ImproperlyConfigured):
            extensions.handle_versioning_setting(cms_config)

    def test_many_to_many_fwd_rel_doesnt_raise_exception_if_function_provided(self):
        extensions = VersioningCMSExtension()
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning=[
                VersionableItem(
                    content_model=relationship_models.ContentManytoManyF,
                    grouper_field_name='grouper',
                    copy_functions={
                        'rel': lambda old_value: old_value
                    }
                )
            ]
        )
        try:
            extensions.handle_versioning_setting(cms_config)
        except ImproperlyConfigured:
            self.fail("Unexpectedly raised ImproperlyConfigured")

    def test_many_to_many_bwd_rel_raises_exception_if_function_not_provided(self):
        extensions = VersioningCMSExtension()
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning=[
                VersionableItem(
                    content_model=relationship_models.ContentManytoManyB,
                    grouper_field_name='grouper',
                )
            ]
        )
        with self.assertRaises(ImproperlyConfigured):
            extensions.handle_versioning_setting(cms_config)

    def test_many_to_many_bwd_rel_doesnt_raise_exception_if_function_provided(self):
        extensions = VersioningCMSExtension()
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning=[
                VersionableItem(
                    content_model=relationship_models.ContentManytoManyB,
                    grouper_field_name='grouper',
                    copy_functions={
                        'manytomanyb.rel': lambda old_value: old_value
                    }
                )
            ]
        )
        try:
            extensions.handle_versioning_setting(cms_config)
        except ImproperlyConfigured:
            self.fail("Unexpectedly raised ImproperlyConfigured")

    def test_generic_rel_raises_exception_if_function_not_provided(self):
        extensions = VersioningCMSExtension()
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning=[
                VersionableItem(
                    content_model=relationship_models.ContentGeneric,
                    grouper_field_name='grouper',
                )
            ]
        )
        with self.assertRaises(ImproperlyConfigured):
            extensions.handle_versioning_setting(cms_config)

    def test_generic_fwd_rel_doesnt_raise_exception_if_function_provided(self):
        extensions = VersioningCMSExtension()
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning=[
                VersionableItem(
                    content_model=relationship_models.ContentGeneric,
                    grouper_field_name='grouper',
                    copy_functions={
                        'rel': lambda old_value: old_value
                    }
                )
            ]
        )
        try:
            extensions.handle_versioning_setting(cms_config)
        except ImproperlyConfigured:
            self.fail("Unexpectedly raised ImproperlyConfigured")


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
        # Check that Comments were not registered to the admin
        # (they are defined in cms_config.py but are not registered
        # to the admin)
        self.assertNotIn(Comment, admin.site._registry)
