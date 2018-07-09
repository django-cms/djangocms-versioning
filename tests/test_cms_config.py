from mock import Mock

from django.core.exceptions import ImproperlyConfigured
from django.apps import apps

from cms.app_registration import get_cms_extension_apps, get_cms_config_apps
from cms.test_utils.testcases import CMSTestCase
from cms.utils.setup import setup_cms_apps

from djangocms_versioning.cms_config import VersioningCMSExtension
from djangocms_versioning.test_utils.polls.models import PollVersion
from djangocms_versioning.test_utils.blogpost.models import BlogPostVersion


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


# class CMSConfigComponentTestCase(CMSTestCase):
#
#     def test_version_model_appends(self):
#         extensions = VersioningCMSExtension()
#         cms_config1 = Mock(spec=[],
#                            djangocms_versioning_enabled=True,
#                            versioning_models=[{'a': 111}],
#                            versioning_content_types={
#                                'grouper': 'post',
#                                'content': '.....',
#                                'version': '# insert_version_object'})
#
#         cms_config2 = Mock(spec=[],
#                            djangocms_versioning_enabled=True,
#                            versioning_models=[{'b': 222}],
#                            versioning_content_types={
#                                'grouper': 'post',
#                                'content': '.....',
#                                'version': '# insert_version_object'})
#
#         extensions.configure_app(cms_config1)
#         extensions.configure_app(cms_config2)
#
#         self.assertListEqual(extensions.get_version_models(), [{'a': 111}, {'b': 222}])


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

