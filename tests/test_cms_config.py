from collections import OrderedDict
from unittest.mock import Mock, patch

from cms.admin.forms import ChangePageForm
from cms.models import Page
from cms.test_utils.testcases import CMSTestCase
from django.apps import apps
from django.contrib import admin
from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory
from django.utils.text import slugify

from djangocms_versioning.admin import VersionAdmin, VersioningAdminMixin
from djangocms_versioning.cms_config import (
    VersioningCMSConfig,
    VersioningCMSExtension,
)
from djangocms_versioning.constants import DRAFT
from djangocms_versioning.datastructures import VersionableItem, default_copy
from djangocms_versioning.models import Version
from djangocms_versioning.test_utils import factories
from djangocms_versioning.test_utils.blogpost.cms_config import (
    BlogpostCMSConfig,
)
from djangocms_versioning.test_utils.blogpost.models import (
    BlogContent,
    Comment,
)
from djangocms_versioning.test_utils.incorrectly_configured_blogpost.cms_config import (
    IncorrectBlogpostCMSConfig,
)
from djangocms_versioning.test_utils.polls.cms_config import PollsCMSConfig
from djangocms_versioning.test_utils.polls.models import Poll, PollContent

req_factory = RequestFactory()


class PageContentVersioningBehaviourTestCase(CMSTestCase):

    def setUp(self):
        self.site = Site.objects.get_current()
        self.user = self.get_superuser()
        self.language = "en"
        self.title = "test page"

        self.version = factories.PageVersionFactory(content__language="en", state=DRAFT,)
        factories.PageUrlFactory(
            page=self.version.content.page,
            language="en",
            path=slugify(self.title),
            slug=slugify(self.title),
        )

        self.page = self.version.content.page
        self.content = self.version.content

    def test_saving_draft_has_pageurl(self):
        """A draft has pageurl as normal"""
        url = self.page.get_urls().first()

        self.assertEqual(self.version.state, DRAFT)
        self.assertEqual(url.path, slugify(self.title))

    def test_publishing_draft_retains_pageurl(self):
        """We publish a version, pageurl is still the same"""
        self.version.publish(self.user)

        url = self.page.get_urls().first()
        self.assertEqual(url.path, slugify(self.title))

    def test_published_version_with_new_version_retains_pageurl(self):
        """
        We have a published page and we create a new version and publish that.
        PageUrl path stays the same
        """
        self.version.publish(self.user)
        v2 = self.version.copy(self.user)
        v2.publish(self.user)

        page = Page.objects.get(pk=self.page.pk)
        url = page.get_urls().first()

        self.assertEqual(url.path, slugify(self.title))

    def test_published_version_with_new_version_retains_pageurl_unmanaged(self):
        """We have a published page and we create a new version and publish that.
        The url in question is unmanaged and stays the same.

        The path was previously set to None on unpublish. This deleted the
        url a content editor had put in the field "overwrite url".
        Putting anything into the field "overwrite url" sets the property
        managed to False.
        """
        url = self.page.get_urls().first()
        url.managed = False
        url.save()

        self.version.publish(self.user)
        v2 = self.version.copy(self.user)
        v2.publish(self.user)

        page = Page.objects.get(pk=self.page.pk)
        url = page.get_urls().first()

        self.assertEqual(url.path, slugify(self.title))

    def test_changing_slug_changes_page_url(self):
        """Using change form to change title / slug updates path?"""
        new_slug = "new-slug-here"
        data = {
            "title": self.content.title,
            "slug": new_slug
        }

        request = req_factory.get("/?language=en")
        request.user = self.user

        form = ChangePageForm(data, instance=self.content)
        form._request = request
        form._site = self.site
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

        form.save()
        page = Page.objects.get(pk=self.page.pk)
        url = page.get_urls().first()

        self.assertEqual(url.slug, new_slug)
        self.assertEqual(url.path, new_slug)


class VersioningExtensionUnitTestCase(CMSTestCase):
    def test_raises_exception_if_neither_versioning_nor_context_setting_specified(self):
        """
        Tests, if neither the versioning attribute or the
        versioning_add_to_confirmation_context attribute has been specified,
        an ImproperlyConfigured exception is raised
        """
        extensions = VersioningCMSExtension()
        cms_config = Mock(spec=[], djangocms_versioning_enabled=True)
        with self.assertRaises(ImproperlyConfigured):
            extensions.configure_app(cms_config)

    def test_raises_exception_if_versioning_not_iterable(self):
        """Tests ImproperlyConfigured exception is raised if
        versioning setting is not an iterable
        """
        extensions = VersioningCMSExtension()
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning=VersionableItem(
                content_model=PollContent,
                grouper_field_name="poll",
                copy_function=default_copy,
            ),
        )
        with self.assertRaises(ImproperlyConfigured):
            extensions.configure_app(cms_config)

    def test_raises_exception_if_not_versionable_class(self):
        """Tests ImproperlyConfigured exception is raised if elements
        in the versioning list are not instances of VersionableItem classes
        """
        extensions = VersioningCMSExtension()
        cms_config = Mock(
            spec=[], djangocms_versioning_enabled=True, versioning=["aaa", {}]
        )
        with self.assertRaises(ImproperlyConfigured):
            extensions.configure_app(cms_config)

    def test_raises_exception_if_content_class_already_registered_in_same_config(self):
        """Tests ImproperlyConfigured exception is raised if the same
        content class is registered twice in the same config file
        """
        extension = VersioningCMSExtension()
        poll_versionable = VersionableItem(
            content_model=PollContent,
            grouper_field_name="poll",
            copy_function=default_copy,
        )
        poll_versionable2 = VersionableItem(
            content_model=PollContent,
            grouper_field_name="poll",
            copy_function=default_copy,
        )
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning=[poll_versionable, poll_versionable2],
        )
        with self.assertRaises(ImproperlyConfigured):
            extension.configure_app(cms_config)

    def test_raises_exception_if_content_class_already_registered_in_different_config(
        self
    ):
        """Tests ImproperlyConfigured exception is raised if the same
        content class is registered twice in different config files
        """
        extension = VersioningCMSExtension()
        poll_versionable = VersionableItem(
            content_model=PollContent,
            grouper_field_name="poll",
            copy_function=default_copy,
        )
        poll_versionable2 = VersionableItem(
            content_model=PollContent,
            grouper_field_name="poll",
            copy_function=default_copy,
        )
        cms_config1 = Mock(
            spec=[], djangocms_versioning_enabled=True, versioning=[poll_versionable]
        )
        cms_config2 = Mock(
            spec=[], djangocms_versioning_enabled=True, versioning=[poll_versionable2]
        )
        with self.assertRaises(ImproperlyConfigured):
            extension.handle_versioning_setting(cms_config1)
            extension.handle_versioning_setting(cms_config2)

    def test_versioning_add_to_confirmation_context_is_an_optional_setting(self):
        extension = VersioningCMSExtension()
        poll_versionable = VersionableItem(
            content_model=PollContent,
            grouper_field_name="poll",
            copy_function=default_copy,
        )
        cms_config = Mock(
            spec=[], djangocms_versioning_enabled=True, versioning=[poll_versionable]
        )
        try:
            extension.configure_app(cms_config)
        except ImproperlyConfigured:
            self.fail(
                "versioning_add_to_confirmation_context setting should be optional"
            )

    def test_raises_exception_if_unsupported_key_added_to_add_to_context(self):
        """Tests ImproperlyConfigured exception is raised if an unsupported
        dict key is used for the versioning_add_to_confirmation_context setting
        """
        extension = VersioningCMSExtension()
        poll_versionable = VersionableItem(
            content_model=PollContent,
            grouper_field_name="poll",
            copy_function=default_copy,
        )
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning=[poll_versionable],
            # versioning doesn't know what red rabbits is
            # so this should raise an exception
            versioning_add_to_confirmation_context={
                "red_rabbits": OrderedDict({"rabbit": lambda r, v: v.content})
            },
        )
        with self.assertRaises(ImproperlyConfigured):
            extension.configure_app(cms_config)

    def test_versionables_list_created(self):
        """Test handle_versioning_setting method adds all the
        models into the versionables list
        """
        extension = VersioningCMSExtension()
        poll_versionable = VersionableItem(
            content_model=PollContent,
            grouper_field_name="poll",
            copy_function=default_copy,
        )
        blog_versionable = VersionableItem(
            content_model=BlogContent,
            grouper_field_name="blogpost",
            copy_function=default_copy,
        )
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning=[poll_versionable, blog_versionable],
        )
        extension.configure_app(cms_config)
        self.assertListEqual(
            extension.versionables, [poll_versionable, blog_versionable]
        )

    def test_context_dict_created(self):
        """Test a dict is populated from the versioning_add_to_confirmation_context
        config
        """
        extension = VersioningCMSExtension()

        def unpublish_context1(request, version, *args, **kwargs):
            return "Every time you unpublish something you should kiss a cat"

        def unpublish_context2(request, version, *args, **kwargs):
            return "Good luck with your unpublishing"

        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning_add_to_confirmation_context={
                "unpublish": OrderedDict(
                    {"1": unpublish_context1, "2": unpublish_context2}
                )
            },
        )
        extension.configure_app(cms_config)
        expected = {
            "unpublish": OrderedDict({"1": unpublish_context1, "2": unpublish_context2})
        }
        self.assertDictEqual(extension.add_to_context, expected)

    def test_context_dict_doesnt_get_overwritten(self):
        """Test when multiple apps update the same key in the context dict,
        values from both apps end up under that key
        """
        extension = VersioningCMSExtension()

        def unpublish_context1(request, version, *args, **kwargs):
            return "Cats don't like to be unpublished"

        def unpublish_context2(request, version, *args, **kwargs):
            return "Elephants don't mind being unpublished'"

        cms_config1 = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning_add_to_confirmation_context={
                "unpublish": OrderedDict([("1", unpublish_context1)])
            },
        )
        cms_config2 = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning_add_to_confirmation_context={
                "unpublish": OrderedDict([("2", unpublish_context2)])
            },
        )

        extension.configure_app(cms_config1)
        extension.configure_app(cms_config2)

        expected = {
            "unpublish": OrderedDict(
                [("1", unpublish_context1), ("2", unpublish_context2)]
            )
        }
        self.assertDictEqual(extension.add_to_context, expected)

    def test_handle_content_admin_classes(self):
        """Test handle_admin_classes replaces the admin model class
        with an admin model class that inherits from VersioningAdminMixin
        """
        extensions = VersioningCMSExtension()
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning=[
                VersionableItem(
                    content_model=PollContent,
                    grouper_field_name="poll",
                    copy_function=default_copy,
                )
            ],
        )
        extensions.handle_admin_classes(cms_config)
        self.assertIn(PollContent, admin.site._registry)
        self.assertIn(
            VersioningAdminMixin, admin.site._registry[PollContent].__class__.mro()
        )

    def test_is_content_model_versioned(self):
        """Test that is_content_model_versioned returns True for
        content model that's versioned
        """
        extension = VersioningCMSExtension()
        extension.versionables = [
            VersionableItem(
                content_model=PollContent,
                grouper_field_name="poll",
                copy_function=default_copy,
            )
        ]

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
            spec=[],
            djangocms_versioning_enabled=True,
            content_model=PollContent,
            concrete=True,
            grouper_model=Poll,
            version_model_proxy=apps.get_model(
                "djangocms_versioning", "PollContentVersion"
            ),
        )

        with patch.object(versionable, "version_model_proxy"):
            extensions = VersioningCMSExtension()
            cms_config = Mock(
                spec=[], djangocms_versioning_enabled=True, versioning=[versionable]
            )
            extensions.handle_version_admin(cms_config)
        self.assertIn(versionable.version_model_proxy, admin.site._registry)
        self.assertIn(
            VersionAdmin,
            admin.site._registry[versionable.version_model_proxy].__class__.mro(),
        )

    def test_field_extension_populates(self):
        """
        With proper configuration provided, cms extension populates
        """
        def poll_modifier(obj, field):
            return obj

        extensions = VersioningCMSExtension()
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning=[
                VersionableItem(
                    content_model=PollContent,
                    grouper_field_name="poll",
                    copy_function=default_copy,
                )
            ],
            extended_admin_field_modifiers=[{PollContent: {"text": poll_modifier}}, ]
        )
        extensions.handle_admin_field_modifiers(cms_config)

        self.assertEqual(extensions.add_to_field_extension, {PollContent: {"text": poll_modifier}})

    def test_field_extension_proper_error_non_iterable(self):
        """
        When a non-iterable is passed as the method for modifying a field,
        raise ImproperlyConfigured
        """
        def poll_modifier(obj, field):
            return obj

        extensions = VersioningCMSExtension()
        cms_config = Mock(
            spec=[],
            djangocms_versioning_enabled=True,
            versioning=[
                VersionableItem(
                    content_model=PollContent,
                    grouper_field_name="poll",
                    copy_function=default_copy,
                )
            ],
            extended_admin_field_modifiers=(PollContent, "text", poll_modifier)
        )

        with self.assertRaises(ImproperlyConfigured):
            extensions.handle_admin_field_modifiers(cms_config)


# NOTE: These tests simply test what has already happened on start up
# when the app registry has been instantiated.
class VersioningIntegrationTestCase(CMSTestCase):
    def test_all_versionables_collected(self):
        """Check that all version models defined in cms_config.py
        are collected into a list
        """
        app = apps.get_app_config("djangocms_versioning")
        page_versionable = VersioningCMSConfig.versioning[0]
        poll_versionable = PollsCMSConfig.versioning[0]
        blog_versionable = BlogpostCMSConfig.versioning[0]
        comment_versionable = BlogpostCMSConfig.versioning[1]
        incorrect_blog_versionable = IncorrectBlogpostCMSConfig.versioning[0]
        self.assertListEqual(
            app.cms_extension.versionables,
            [page_versionable, poll_versionable, blog_versionable, comment_versionable, incorrect_blog_versionable],
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
            VersioningAdminMixin, admin.site._registry[PollContent].__class__.mro()
        )
        # Check BlogContent has had its admin class modified
        self.assertIn(BlogContent, admin.site._registry)
        self.assertIn(
            VersioningAdminMixin, admin.site._registry[BlogContent].__class__.mro()
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
            admin.site._registry[source_model_to_proxy[PollContent]].__class__.mro(),
        )

        self.assertIn(BlogContent, source_models_in_proxies)
        self.assertIn(
            VersionAdmin,
            admin.site._registry[source_model_to_proxy[BlogContent]].__class__.mro(),
        )

        self.assertNotIn(Comment, source_models_in_proxies)
