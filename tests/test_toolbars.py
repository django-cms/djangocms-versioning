from django.test import RequestFactory

from cms.test_utils.testcases import CMSTestCase
from cms.toolbar.toolbar import CMSToolbar

from djangocms_versioning import constants
from djangocms_versioning.cms_toolbars import VersioningToolbar
from djangocms_versioning.test_utils.factories import (
    PollVersionFactory,
    UserFactory,
)
from djangocms_versioning.test_utils.polls.cms_config import PollsCMSConfig


class VersioningToolbarTestCase(CMSTestCase):

    def _get_toolbar(self, content_obj):
        """Helper method to set up the toolbar
        """
        request = RequestFactory().get('/')
        request.user = UserFactory()
        request.session = {}
        cms_toolbar = CMSToolbar(request)
        toolbar = VersioningToolbar(
            request, toolbar=cms_toolbar, is_current_app=True, app_path='/')
        toolbar.toolbar.obj = content_obj
        return toolbar

    def _get_publish_url(self, version):
        """Helper method to return the expected publish url
        """
        versionable = PollsCMSConfig.versioning[0]
        admin_url = self.get_admin_url(
            versionable.version_model_proxy, 'publish', version.pk)
        return admin_url

    def test_publish_in_toolbar_for_draft_version(self):
        version = PollVersionFactory(state=constants.DRAFT)
        toolbar = self._get_toolbar(version.content)

        toolbar.post_template_populate()

        publish_button = toolbar.toolbar.get_right_items()[0].buttons[0]
        self.assertEqual(publish_button.name, 'Publish')
        self.assertEqual(publish_button.url, self._get_publish_url(version))
        self.assertFalse(publish_button.disabled)

    def test_publish_not_in_toolbar_for_archived_version(self):
        version = PollVersionFactory(state=constants.ARCHIVED)
        toolbar = self._get_toolbar(version.content)

        toolbar.post_template_populate()

        self.assertListEqual(
            toolbar.toolbar.get_right_items()[0].buttons, [])

    def test_publish_not_in_toolbar_for_published_version(self):
        version = PollVersionFactory(state=constants.PUBLISHED)
        toolbar = self._get_toolbar(version.content)

        toolbar.post_template_populate()

        self.assertListEqual(
            toolbar.toolbar.get_right_items()[0].buttons, [])

    def test_publish_not_in_toolbar_for_unpublished_version(self):
        version = PollVersionFactory(state=constants.UNPUBLISHED)
        toolbar = self._get_toolbar(version.content)

        toolbar.post_template_populate()

        self.assertListEqual(
            toolbar.toolbar.get_right_items()[0].buttons, [])

    def test_dont_add_publish_for_models_not_registered_with_versioning(self):
        # User objects are not registered with versioning, so attempting
        # to populate a user toolbar should not attempt to add a publish
        # button
        toolbar = self._get_toolbar(UserFactory())

        toolbar.post_template_populate()

        self.assertListEqual(
            toolbar.toolbar.get_right_items()[0].buttons, [])
