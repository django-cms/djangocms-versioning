from functools import lru_cache

from cms.toolbar import toolbar

from djangocms_versioning.plugin_rendering import (
    VersionContentRenderer,
    VersionStructureRenderer,
)


@lru_cache(16)
def content_renderer(self):
    return VersionContentRenderer(request=self.request)


toolbar.CMSToolbar.content_renderer = property(content_renderer)  # noqa: E305


@lru_cache(16)
def structure_renderer(self):
    return VersionStructureRenderer(request=self.request)


toolbar.CMSToolbar.structure_renderer = property(
    structure_renderer
)  # noqa: E305
