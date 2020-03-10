from cms import admin
from cms.utils import helpers

from .. import versionables


def get_queryset(func):
    def inner(self, request):
        urls = ("cms_pagecontent_get_tree",)
        queryset = func(self, request)
        if request.resolver_match.url_name in urls:
            versionable = versionables.for_content(queryset.model)
            return queryset.filter(pk__in=versionable.distinct_groupers())
        return queryset

    return inner


admin.pageadmin.PageContentAdmin.get_queryset = get_queryset(
    admin.pageadmin.PageContentAdmin.get_queryset
)


def filter_admin_model(model_class, **kwargs):
    return model_class._original_manager.filter(**kwargs)


helpers.filter_admin_model = filter_admin_model
