from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.dispatch import receiver

from cms import api
from cms.models import Placeholder, pagemodel, titlemodels
from cms.operations import ADD_PAGE_TRANSLATION, CHANGE_PAGE_TRANSLATION
from cms.signals import post_obj_operation
from cms.utils.permissions import _thread_locals

from djangocms_versioning.constants import PUBLISHED
from djangocms_versioning.models import Version


User = get_user_model()

cms_extension = apps.get_app_config("cms").cms_extension


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


def get_placeholders(func):
    def inner(self, language):
        page_content = self.get_title_obj(language)
        return Placeholder.objects.get_for_obj(page_content)

    return inner


pagemodel.Page.get_placeholders = get_placeholders(
    pagemodel.Page.get_placeholders
)  # noqa: E305


@receiver(post_obj_operation)
def pre_page_operation_handler(sender, **kwargs):
    operations = (ADD_PAGE_TRANSLATION, CHANGE_PAGE_TRANSLATION)
    operation_type = kwargs["operation"]

    if operation_type not in operations:
        return

    page = kwargs["obj"]
    language = kwargs["language"]
    cms_extension = apps.get_app_config("djangocms_versioning").cms_extension
    versionable_item = cms_extension.versionables_by_grouper[page.__class__]
    page_contents = (
        versionable_item.for_grouper(page)
        .filter(language=language)
        .values_list("pk", flat=True)
    )
    content_type = ContentType.objects.get_for_model(page_contents.model)
    has_published = Version.objects.filter(
        state=PUBLISHED, content_type=content_type, object_id__in=page_contents
    ).exists()

    if not has_published:
        page.update_urls(language, path=None)
        page._update_url_path_recursive(language)
        page.clear_cache(menu=True)


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
