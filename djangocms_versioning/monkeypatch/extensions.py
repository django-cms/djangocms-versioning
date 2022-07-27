from django.contrib.admin.options import csrf_protect_m
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.urls import reverse


try:
    from cms.extensions.admin import TitleExtensionAdmin
except ImportError:
    from cms.extensions.admin import PageContentExtensionAdmin

from cms.extensions.extension_pool import ExtensionPool
from cms.models import PageContent
from cms.utils.page_permissions import user_can_change_page

from djangocms_versioning.handlers import _update_modified


def _copy_content_extensions(self, source_page, target_page, language, clone=False):
    """
    djangocms-cms/extensions/admin.py, last changed in: divio/django-cms@2894ae8

    The existing method ExtensionPool._copy_title_extensions will only ever
    get published versions, we change the queries to get the latest draft version
    with the _original_manager
    """

    source_title = PageContent._original_manager.filter(
        page=source_page, language=language
    ).first()
    if target_page:
        # the line below has been modified to accommodate versioning.
        target_title = PageContent._original_manager.filter(
            page=target_page, language=language
        ).first()
    else:
        target_title = source_title.publisher_public

    # Compat for change in django-cms
    try:
        # Original v4 attribute
        extensions = self.title_extensions
    except AttributeError:
        # Updated v4 attribute based on `PageContent` extension name change
        extensions = self.page_content_extensions

    for extension in extensions:
        for instance in extension.objects.filter(extended_object=source_title):
            if clone:
                instance.copy(target_title, language)
            else:
                instance.copy_to_public(target_title, language)


# Compat for change in django-cms
try:
    # Original v4 attribute
    ExtensionPool._copy_title_extensions = _copy_content_extensions
except AttributeError:
    # Updated v4 attribute based on `PageContent` extension name change
    ExtensionPool._copy_content_extensions = _copy_content_extensions


def _save_model(self, request, obj, form, change):
    """
    djangocms-cms/extensions/admin.py, last changed in:
    django-cms/django-cms@61e7756a79de0db9671417b44235bbf8866c3c9f

    Ensure that the current page content object can be retrieved. A draft
    object will return an empty set by default hence why we have to remove the
    query manager here!
    """
    if not change and 'extended_object' in request.GET:
        extended_object = PageContent._original_manager.get(
            pk=request.GET['extended_object']
        )
        obj.extended_object = extended_object
        title = extended_object
    else:
        title = obj.extended_object

    if not user_can_change_page(request.user, page=title.page):
        raise PermissionDenied()

    try:
        super(TitleExtensionAdmin, self).save_model(request, obj, form, change)
    except NameError:
        super(PageContentExtensionAdmin, self).save_model(request, obj, form, change)

    # Ensure that we update the version modified date of the attached version
    if title:
        _update_modified(title)


try:
    TitleExtensionAdmin.save_model = _save_model
except NameError:
    PageContentExtensionAdmin.save_model = _save_model


@csrf_protect_m
def _add_view(self, request, form_url='', extra_context=None):
    """
    djangocms-cms/extensions/admin.py, last changed in:
    django-cms/django-cms@61e7756a79de0db9671417b44235bbf8866c3c9f

    Ensure that the current page content object can be retrieved. A draft
    object will return an empty set by default hence why we have to remove the
    query manager here!
    """
    extended_object_id = request.GET.get('extended_object', False)
    if extended_object_id:
        try:
            title = PageContent._original_manager.get(pk=extended_object_id)
            extension = self.model.objects.get(extended_object=title)
            opts = self.model._meta
            change_url = reverse('admin:%s_%s_change' %
                                 (opts.app_label, opts.model_name),
                                 args=(extension.pk,),
                                 current_app=self.admin_site.name)
            return HttpResponseRedirect(change_url)
        except self.model.DoesNotExist:
            pass
    try:
        return super(TitleExtensionAdmin, self).add_view(request, form_url, extra_context)
    except NameError:
        return super(PageContentExtensionAdmin, self).add_view(request, form_url, extra_context)


try:
    TitleExtensionAdmin.add_view = _add_view
except NameError:
    PageContentExtensionAdmin.add_view = _add_view
