from django.apps import apps
from django.contrib.auth import get_user_model

from cms import api
from cms.models import Placeholder, pagemodel
# Compat for change in django-cms
try:
    # Original v4 module
    from cms.models import titlemodels
except ImportError:
    # Updated v4 attribute based on content models module name change
    from cms.models import contentmodels
from cms.utils.permissions import _thread_locals

from djangocms_versioning.models import Version


User = get_user_model()

cms_extension = apps.get_app_config("cms").cms_extension


def _get_page_content_cache(func):
    def inner(self, language, fallback, force_reload):
        prefetch_cache = getattr(self, "_prefetched_objects_cache", {})
        cached_page_content = prefetch_cache.get("pagecontent_set", [])
        for page_content in cached_page_content:
            try:
                self.title_cache[page_content.language] = page_content
            except AttributeError:
                self.page_content_cache[page_content.language] = page_content
        language = func(self, language, fallback, force_reload)
        return language

    return inner

try:
    pagemodel.Page._get_title_cache = _get_page_content_cache(
        pagemodel.Page._get_title_cache
    )  # noqa: E305
except AttributeError:
    pagemodel.Page._get_page_content_cache = _get_page_content_cache(
        pagemodel.Page._get_page_content_cache
    )  # noqa: E305


def get_placeholders(func):
    def inner(self, language):
        try:
            page_content = self.get_title_obj(language)
        except AttributeError:
            page_content = self.get_content_obj(language)
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

# Compat for change in django-cms
try:
    # Original v4 module
    pagecontent_unique_together = tuple(
        set(titlemodels.PageContent._meta.unique_together) - set((("language", "page"),))
    )
    titlemodels.PageContent._meta.unique_together = pagecontent_unique_together
except NameError:
    # Updated v4 attribute based on content models module name change
    pagecontent_unique_together = tuple(
        set(contentmodels.PageContent._meta.unique_together) - set((("language", "page"),))
    )
    contentmodels.PageContent._meta.unique_together = pagecontent_unique_together
