from cms.toolbar import toolbar

from .plugin_rendering import VersionRenderer


def content_renderer(self):
    return VersionRenderer(request=self.request)


toolbar.CMSToolbar.content_renderer = property(content_renderer)
