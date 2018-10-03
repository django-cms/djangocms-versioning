from cms.templatetags import cms_admin
from cms.utils.urlutils import admin_reverse


@cms_admin.register.simple_tag(takes_context=False)
def get_admin_url_for_language(page, language):
    # TODO Perhaps modify get_languages so that it returns
    # only published languages, or add a separate function
    # to do so in places like this.
    existing_language = language in page.get_languages()
    if existing_language:
        page_content = page.get_title_obj(language, fallback=False)
        existing_language = bool(page_content)
    if not existing_language:
        admin_url = admin_reverse('cms_pagecontent_add')
        admin_url += '?cms_page={}&language={}'.format(page.pk, language)
        return admin_url
    return admin_reverse('cms_pagecontent_change', args=[page_content.pk])
cms_admin.get_admin_url_for_language = get_admin_url_for_language  # noqa: E305
