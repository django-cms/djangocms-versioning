from cms.test_utils.testcases import CMSTestCase
from cms.toolbar.toolbar import CMSToolbar

from djangocms_versioning.plugin_rendering import VersionRenderer


class MonkeypatchTestCase(CMSTestCase):

    def test_content_renderer(self):
        """Test that cms.toolbar.toolbar.CMSToolbar.content_renderer
        is replaced with a property returning VersionRenderer
        """
        self.assertEqual(
            CMSToolbar(None).content_renderer.__class__,
            VersionRenderer,
        )
