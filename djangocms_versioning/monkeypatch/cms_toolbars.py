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
        copy = [(code, name) for code, name in languages.items() if code != self.current_lang and (code, name) in remove]

        if add or remove or copy:
            language_menu.add_break(ADD_PAGE_LANGUAGE_BREAK)

        if add:
            add_plugins_menu = language_menu.get_or_create_menu('{0}-add'.format(LANGUAGE_MENU_IDENTIFIER), _('Add Translation'))

            page_add_url = admin_reverse('cms_pagecontent_add')

            for code, name in add:
                url = add_url_parameters(page_add_url, cms_page=self.page.pk, language=code)
                add_plugins_menu.add_modal_item(name, url=url)

        # TODO to enable removal urls you need to overwrite the delete view so that pagecontent is unpublished
        # instead of deleted. Once this work is done the `change_language_menu` monkeypatch can be
        # removed entirely.

        # if remove:
        #     translation_delete_url = admin_reverse('cms_pagecontent_delete', args=(self.title.pk,))

        #     remove_plugins_menu = language_menu.get_or_create_menu('{0}-del'.format(LANGUAGE_MENU_IDENTIFIER), _('Delete Translation'))
        #     disabled = len(remove) == 1
        #     for code, name in remove:
        #         url = add_url_parameters(translation_delete_url, language=code)
        #         remove_plugins_menu.add_modal_item(name, url=url, disabled=disabled)

        if copy:
            copy_plugins_menu = language_menu.get_or_create_menu('{0}-copy'.format(LANGUAGE_MENU_IDENTIFIER), _('Copy all plugins'))
            title = _('from %s')
            question = _('Are you sure you want to copy all plugins from %s?')

            page_copy_url = admin_reverse('cms_pagecontent_copy_language', args=(self.title.pk,))

            for code, name in copy:
                copy_plugins_menu.add_ajax_item(
                    title % name, action=page_copy_url,
                    data={'source_language': code, 'target_language': self.current_lang},
                    question=question % name, on_success=self.toolbar.REFRESH_PAGE
                )



PageToolbar.change_language_menu = change_language_menu  # noqa: E305
