from cms.models import titlemodels
from cms.toolbar import toolbar

from django.utils.functional import cached_property

from .plugin_rendering import VersionRenderer


def content_renderer(self):
    return VersionRenderer(request=self.request)


pagecontent_unique_together = tuple(
    set(titlemodels.PageContent._meta.unique_together) -
    set(('language', 'page'))
)

toolbar.CMSToolbar.content_renderer = cached_property(content_renderer)
titlemodels.PageContent._meta.unique_together = pagecontent_unique_together
