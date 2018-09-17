from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.dispatch import receiver
from django.utils.functional import cached_property

from cms import cms_wizards
from cms.models import titlemodels
from cms.operations import ADD_PAGE_TRANSLATION, CHANGE_PAGE_TRANSLATION
from cms.signals import post_obj_operation
from cms.toolbar import toolbar
from cms.toolbar.utils import get_toolbar_from_request
from cms.utils.conf import get_cms_setting
from menus.menu_pool import MenuRenderer

from .constants import PUBLISHED
from .models import Version
from .plugin_rendering import VersionRenderer


cms_extension = apps.get_app_config('cms').cms_extension


def content_renderer(self):
    return VersionRenderer(request=self.request)


@receiver(post_obj_operation)
def pre_page_operation_handler(sender, **kwargs):
    operations = (ADD_PAGE_TRANSLATION, CHANGE_PAGE_TRANSLATION)
    operation_type = kwargs['operation']

    if operation_type not in operations:
        return

    page = kwargs['obj']
    language = kwargs['language']
    cms_extension = apps.get_app_config('djangocms_versioning').cms_extension
    versionable_item = cms_extension.versionables_by_grouper[page.__class__]
    page_contents = (
        versionable_item
        .for_grouper(page)
        .filter(language=language)
        .values_list('pk', flat=True)
    )
    content_type = ContentType.objects.get_for_model(page_contents.model)
    has_published = (
        Version
        .objects
        .filter(
            state=PUBLISHED,
            content_type=content_type,
            object_id__in=page_contents,
        )
        .exists()
    )

    if not has_published:
        page.update_urls(language, path=None)
        page._update_url_path_recursive(language)
        page.clear_cache(menu=True)


class CreateCMSPageForm(cms_wizards.cms_page_wizard.form):

    def save(self, *args, **kwargs):
        new_page = super(CreateCMSPageForm, self).save(*args, **kwargs)
        page_content = new_page.title_cache[self._language]
        Version.objects.create(content=page_content, created_by=self._request.user)
        return new_page


class CreateCMSSubPageForm(cms_wizards.cms_subpage_wizard.form):

    def save(self, *args, **kwargs):
        new_page = super(CreateCMSSubPageForm, self).save(*args, **kwargs)
        page_content = new_page.title_cache[self._language]
        Version.objects.create(content=page_content, created_by=self._request.user)
        return new_page


pagecontent_unique_together = tuple(
    set(titlemodels.PageContent._meta.unique_together) -
    set((('language', 'page'), ))
)


def menu_renderer_cache_key(self):
    prefix = get_cms_setting('CACHE_PREFIX')

    key = '%smenu_nodes_%s_%s' % (prefix, self.request_language, self.site.pk)

    if self.request.user.is_authenticated:
        key += '_%s_user' % self.request.user.pk

    request_toolbar = get_toolbar_from_request(self.request)

    if request_toolbar.edit_mode_active or request_toolbar.preview_mode_active:
        key += ':draft'
    else:
        key += ':public'
    return key


toolbar.CMSToolbar.content_renderer = cached_property(content_renderer)
titlemodels.PageContent._meta.unique_together = pagecontent_unique_together
cms_extension.wizards[cms_wizards.cms_page_wizard.id].form = CreateCMSPageForm
cms_extension.wizards[cms_wizards.cms_subpage_wizard.id].form = CreateCMSSubPageForm
MenuRenderer.cache_key = property(menu_renderer_cache_key)
