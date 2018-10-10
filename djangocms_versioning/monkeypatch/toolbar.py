from django.utils.functional import cached_property

from cms.toolbar import toolbar

from djangocms_versioning.plugin_rendering import (
    VersionContentRenderer,
    VersionStructureRenderer,
)


def content_renderer(self):
    return VersionContentRenderer(request=self.request)
toolbar.CMSToolbar.content_renderer = cached_property(content_renderer)  # noqa: E305


def structure_renderer(self):
    return VersionStructureRenderer(request=self.request)
toolbar.CMSToolbar.structure_renderer = cached_property(structure_renderer)  # noqa: E305
