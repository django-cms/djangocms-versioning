from django.utils.functional import cached_property

from cms.toolbar import toolbar

from djangocms_versioning.plugin_rendering import VersionRenderer


def content_renderer(self):
    return VersionRenderer(request=self.request)
toolbar.CMSToolbar.content_renderer = cached_property(content_renderer)  # noqa: E305
