from django.apps import apps
from django.contrib.auth import get_user_model

from cms import api
from cms.models import Placeholder, pagemodel, titlemodels
from cms.utils.permissions import _thread_locals

from djangocms_versioning.models import Version


User = get_user_model()

cms_extension = apps.get_app_config("cms").cms_extension


def _get_admin_title_cache(page, language, fallback, force_reload):
    from cms.utils import i18n
    from django.utils.translation import get_language

    def get_fallback_language(page, language):
        fallback_langs = i18n.get_fallback_languages(language)
        for lang in fallback_langs:
            if page.admin_title_cache.get(lang):
                return lang

    if not language:
        language = get_language()

    force_reload = (force_reload or language not in page.admin_title_cache)
    if force_reload:
        from cms.models import PageContent
        titles = PageContent._original_manager.filter(page=page)
        for title in titles:
            page.admin_title_cache[title.language] = title

    if page.admin_title_cache.get(language):
        return language

    use_fallback = all([
        fallback,
        not page.admin_title_cache.get(language),
        get_fallback_language(page, language)
    ])
    if use_fallback:
        # language can be in the cache but might be an EmptyPageContent instance
        return get_fallback_language(page, language)
    return language


def _get_title_cache(func):
    def inner(self, language, fallback, force_reload):
        prefetch_cache = getattr(self, "_prefetched_objects_cache", {})
        cached_page_content = prefetch_cache.get("pagecontent_set", [])
        for page_content in cached_page_content:
            self.title_cache[page_content.language] = page_content
        language = func(self, language, fallback, force_reload)
        return language

    return inner


pagemodel.Page._get_title_cache = _get_title_cache(
    pagemodel.Page._get_title_cache
)  # noqa: E305


def get_admin_title_obj(self, language=None, fallback=False, force_reload=False):
    language = _get_admin_title_cache(self, language, fallback, force_reload)

    if language in self.admin_title_cache:
        return self.admin_title_cache[language]
    from cms.models import EmptyPageContent

    return EmptyPageContent(language)


pagemodel.Page.get_admin_title_obj = get_admin_title_obj


def get_placeholders(func):
    def inner(self, language):
        page_content = self.get_title_obj(language)
        return Placeholder.objects.get_for_obj(page_content)

    return inner


pagemodel.Page.get_placeholders = get_placeholders(
    pagemodel.Page.get_placeholders
)  # noqa: E305


def create_title(func):
    def inner(language, title, page, **kwargs):
        created_by = kwargs.get("created_by")
        if not isinstance(created_by, User):
            created_by = getattr(_thread_locals, "user", None)
        assert created_by is not None, (
            "With versioning enabled, create_title requires a User instance"
            " to be passed as created_by parameter"
        )
        page_content = func(language, title, page, **kwargs)
        Version.objects.create(content=page_content, created_by=created_by)
        return page_content

    return inner


api.create_title = create_title(api.create_title)  # noqa: E305


pagecontent_unique_together = tuple(
    set(titlemodels.PageContent._meta.unique_together) - set((("language", "page"),))
)
titlemodels.PageContent._meta.unique_together = pagecontent_unique_together
