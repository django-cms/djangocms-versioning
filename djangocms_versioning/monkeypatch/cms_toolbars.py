from django.utils.translation import ugettext_lazy as _

from cms.cms_toolbars import (
    ADD_PAGE_LANGUAGE_BREAK,
    LANGUAGE_MENU_IDENTIFIER,
    PageToolbar,
)
from cms.utils import page_permissions
from cms.utils.i18n import get_language_dict
from cms.utils.urlutils import add_url_parameters, admin_reverse


def change_language_menu(self):
    if self.toolbar.edit_mode_active and self.page:
        can_change = page_permissions.user_can_change_page(
            user=self.request.user,
            page=self.page,
            site=self.current_site,
        )
    else:
        can_change = False

    if can_change:
        language_menu = self.toolbar.get_menu(LANGUAGE_MENU_IDENTIFIER)
        if not language_menu:
            return None

        languages = get_language_dict(self.current_site.pk)

        remove = [(code, languages.get(code, code)) for code in self.page.get_languages() if code in languages]
        add = [l for l in languages.items() if l not in remove]

        if add:
            language_menu.add_break(ADD_PAGE_LANGUAGE_BREAK)

            add_plugins_menu = language_menu.get_or_create_menu(
                '{0}-add'.format(LANGUAGE_MENU_IDENTIFIER),
                _('Add Translation')
            )

            page_add_url = admin_reverse('cms_pagecontent_add')

            for code, name in add:
                url = add_url_parameters(page_add_url, cms_page=self.page.pk, language=code)
                add_plugins_menu.add_modal_item(name, url=url)
PageToolbar.change_language_menu = change_language_menu  # noqa: E305
