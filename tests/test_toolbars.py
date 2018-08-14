from django.test import RequestFactory

from cms.test_utils.testcases import CMSTestCase
from cms.toolbar.toolbar import CMSToolbar

from djangocms_versioning.cms_toolbars import VersioningToolbar
from djangocms_versioning.test_utils.factories import (
    UserFactory, PollVersionFactory)
from djangocms_versioning.test_utils.polls.cms_config import PollsCMSConfig


class VersioningToolbarTestCase(CMSTestCase):
    # TODO: Only show publish link for drafts

    def setUp(self):
        self.version = PollVersionFactory()

    def _get_toolbar(self):
        request = RequestFactory().get('/')
        request.user = UserFactory()
        request.session = {}
        cms_toolbar = CMSToolbar(request)
        toolbar = VersioningToolbar(
            request, toolbar=cms_toolbar, is_current_app=True, app_path='/')
        toolbar.toolbar.obj = self.version.content
        return toolbar

    def _get_admin_url(self):
        versionable = PollsCMSConfig.versioning[0]
        admin_url = self.get_admin_url(
            versionable.version_model_proxy, 'publish', self.version.pk)
        return admin_url

    def test_publish_button_added(self):
        toolbar = self._get_toolbar()

        toolbar.post_template_populate()

        publish_button = toolbar.toolbar.get_right_items()[0].buttons[0]
        self.assertEqual(publish_button.name, 'Publish')
        self.assertEqual(publish_button.url, self._get_admin_url())
        self.assertFalse(publish_button.disabled)
