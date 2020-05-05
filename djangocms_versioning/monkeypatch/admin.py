from cms import admin
from cms.utils import get_language_from_request, helpers

from .. import versionables


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
