from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
)
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from cms import admin
from cms.models import PageContent
from cms.utils import get_language_from_request, helpers
from cms.utils.i18n import get_language_list
from cms.utils.plugins import copy_plugins_to_placeholder

from djangocms_versioning import versionables
from djangocms_versioning.helpers import get_latest_admin_viewable_page_content


def get_queryset(func):
    def inner(self, request):
        urls = ("cms_pagecontent_get_tree",)
        queryset = func(self, request)
        if request.resolver_match.url_name in urls:
            versionable = versionables.for_content(queryset.model)

            # TODO: Improve the grouping filters to use anything defined in the
            #       apps versioning config extra_grouping_fields
            grouping_filters = {}
            if 'language' in versionable.extra_grouping_fields:
                grouping_filters['language'] = get_language_from_request(request)

            return queryset.filter(pk__in=versionable.distinct_groupers(**grouping_filters))
        return queryset

    return inner


admin.pageadmin.PageContentAdmin.get_queryset = get_queryset(
    admin.pageadmin.PageContentAdmin.get_queryset
)


def get_admin_model_object_by_id(model_class, obj_id):
    return model_class._original_manager.get(pk=obj_id)


helpers.get_admin_model_object_by_id = get_admin_model_object_by_id


# CAVEAT:
#   - PageContent contains the template, this can differ for each language,
#     it is assumed that templates would be the same when copying from one language to another
# FIXME: This monkeypatch exists to allow the language copy feature to work
#        The long term solution will require knowing:
#           - why this view is an ajax call
#           - where it should live going forwards (cms vs versioning)
#           - A better way of making the feature extensible / modifiable for versioning
def copy_language(self, request, object_id):
    target_language = request.POST.get('target_language')

    # CAVEAT: Avoiding self.get_object because it sets the page cache,
    #         We don't want a draft showing to a regular site visitor!
    #         source_page_content = self.get_object(request, object_id=object_id)
    source_page_content = PageContent._original_manager.get(pk=object_id)

    if not self.has_change_permission(request, obj=source_page_content):
        raise PermissionDenied

    if source_page_content is None:
        raise self._get_404_exception(object_id)

    page = source_page_content.page

    if not target_language or not target_language in get_language_list(site_id=page.node.site_id):
        return HttpResponseBadRequest(force_text(_("Language must be set to a supported language!")))

    target_page_content = get_latest_admin_viewable_page_content(page, target_language)

    for placeholder in source_page_content.get_placeholders():
        # Try and get a matching placeholder, only if it exists
        try:
            target = target_page_content.get_placeholders().get(slot=placeholder.slot)
        except ObjectDoesNotExist:
            continue

        plugins = placeholder.get_plugins_list(source_page_content.language)

        if not target.has_add_plugins_permission(request.user, plugins):
            return HttpResponseForbidden(force_text(_('You do not have permission to copy these plugins.')))
        copy_plugins_to_placeholder(plugins, target, language=target_language)
    return HttpResponse("ok")


admin.pageadmin.PageContentAdmin.copy_language = copy_language
