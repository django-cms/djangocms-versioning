from cms.toolbar.utils import get_toolbar_from_request
from cms.utils.conf import get_cms_setting
from menus.menu_pool import MenuRenderer


def menu_renderer_cache_key(self):
    prefix = get_cms_setting("CACHE_PREFIX")

    key = "%smenu_nodes_%s_%s" % (prefix, self.request_language, self.site.pk)

    if self.request.user.is_authenticated:
        key += "_%s_user" % self.request.user.pk

    request_toolbar = get_toolbar_from_request(self.request)

    if request_toolbar.edit_mode_active or request_toolbar.preview_mode_active:
        key += ":draft"
    else:
        key += ":public"
    return key


MenuRenderer.cache_key = property(menu_renderer_cache_key)  # noqa: E305
