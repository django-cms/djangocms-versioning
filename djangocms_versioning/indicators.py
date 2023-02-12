import json

from django.contrib.auth import get_permission_codename
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _

from cms.utils.urlutils import static_with_version

from djangocms_versioning import versionables
from djangocms_versioning.constants import (
    ARCHIVED,
    DRAFT,
    PUBLISHED,
    UNPUBLISHED,
    VERSION_STATES,
)
from djangocms_versioning.helpers import (
    get_latest_admin_viewable_content,
    version_list_url,
)
from djangocms_versioning.models import Version


indicator_description = {
    "published": _("Published"),
    "dirty": _("Changed"),
    "draft": _("Draft"),
    "unpublished": _("Unpublished"),
    "archived": _("Archived"),
    "empty": _("Empty"),
}


def _reverse_action(version, action, back=None):
    get_params = f"?{urlencode(dict(back=back))}" if back else ""
    return reverse(
        f"admin:{version._meta.app_label}_{version.versionable.version_model_proxy._meta.model_name}_{action}",
        args=(version.pk,)
    ) + get_params


def content_indicator_menu(request, status, versions, back=""):
    menu = []
    if request.user.has_perm(f"cms.{get_permission_codename('change', versions[0]._meta)}"):
        if versions[0].check_publish.as_bool(request.user):
            menu.append((
                _("Publish"), "cms-icon-publish",
                _reverse_action(versions[0], "publish"),
                "js-cms-tree-lang-trigger",  # Triggers POST from the frontend
            ))
        if versions[0].check_edit_redirect.as_bool(request.user) and versions[0].state == PUBLISHED:
            menu.append((
                _("Create new draft"), "cms-icon-edit-new",
                _reverse_action(versions[0], "edit_redirect"),
                "js-cms-tree-lang-trigger js-cms-pagetree-page-view",  # Triggers POST from the frontend
            ))
        if versions[0].check_revert.as_bool(request.user) and versions[0].state == UNPUBLISHED:
            # Do not offer revert from unpublish -> archived versions to be managed in version admin
            label = _("Revert from Unpublish")
            menu.append((
                label, "cms-icon-undo",
                _reverse_action(versions[0], "revert"),
                "js-cms-tree-lang-trigger",  # Triggers POST from the frontend
            ))
        if versions[0].check_unpublish.as_bool(request.user):
            menu.append((
                _("Unpublish"), "cms-icon-unpublish",
                _reverse_action(versions[0], "unpublish"),
                "js-cms-tree-lang-trigger",
            ))
        if len(versions) > 1 and versions[1].check_unpublish.as_bool(request.user):
            menu.append((
                _("Unpublish"), "cms-icon-unpublish",
                _reverse_action(versions[1], "unpublish"),
                "js-cms-tree-lang-trigger",
            ))
        if versions[0].check_discard.as_bool(request.user):
            menu.append((
                _("Delete Draft") if status == DRAFT else _("Delete Changes"), "cms-icon-bin",
                _reverse_action(versions[0], "discard", back=back),
                "",  # Let view ask for confirmation
            ))
        if len(versions) >= 2 and versions[0].state == DRAFT and versions[1].state == PUBLISHED:
            menu.append((
                _("Compare Draft to Published..."), "cms-icon-layers",
                _reverse_action(versions[1], "compare") +
                "?" + urlencode(dict(
                    compare_to=versions[0].pk,
                    back=back,
                )),
                "",
            ))
    menu.append(
        (
            _("Manage Versions..."), "cms-icon-copy",
            version_list_url(versions[0].content),
            "",
        )
    )
    return menu


def content_indicator(content_obj):
    """Translates available versions into status to be reflected by the indicator.
    Function caches the result in the page_content object"""

    if not content_obj:
        return None  # pragma: no cover
    elif not hasattr(content_obj, "_indicator_status"):
        versions = Version.objects.filter_by_content_grouping_values(
            content_obj
        ).order_by("-pk")
        signature = {
            state: versions.filter(state=state)
            for state, name in VERSION_STATES
        }
        if signature[DRAFT] and not signature[PUBLISHED]:
            content_obj._indicator_status = "draft"
            content_obj._version = signature[DRAFT]
        elif signature[DRAFT] and signature[PUBLISHED]:
            content_obj._indicator_status = "dirty"
            content_obj._version = (signature[DRAFT][0], signature[PUBLISHED][0])
        elif signature[PUBLISHED]:
            content_obj._indicator_status = "published"
            content_obj._version = signature[PUBLISHED]
        elif signature[UNPUBLISHED]:
            content_obj._indicator_status = "unpublished"
            content_obj._version = signature[UNPUBLISHED]
        elif signature[ARCHIVED]:
            content_obj._indicator_status = "archived"
            content_obj._version = signature[ARCHIVED]
        else:
            content_obj._indicator_status = None
            content_obj._version = [None]
    return content_obj._indicator_status


def is_editable(content_obj, request):
    """Check of content_obj is editable"""
    if not content_obj.content_indicator():
        # Something's wrong: content indicator not identified. Maybe no version?
        return False
    versions = content_obj._version
    return versions[0].check_modify.as_bool(request.user)


class IndicatorMixin:
    """Mixin to provide indicator column to the changelist view of a content model admin. Usage::

        class MyContentModelAdmin(ContenModelAdminMixin, admin.ModelAdmin):
            list_display = [...]

            def get_list_display(self, request):
                return self.list_display + [
                    self.get_indicator_column(request)
                ]
    """
    class Media:
        # js for the context menu
        js = ("djangocms_versioning/js/indicators.js",)
        # css for indicators and context menu
        css = {
            "all": (static_with_version("cms/css/cms.pagetree.css"),),
        }

    indicator_column_label = _("State")

    @property
    def _extra_grouping_fields(self):
        try:
            return versionables.for_grouper(self.model).extra_grouping_fields
        except KeyError:
            return None

    def get_indicator_column(self, request):
        def indicator(obj):
            if self._extra_grouping_fields is not None:  # Grouper Model
                content_obj = get_latest_admin_viewable_content(obj, include_unpublished_archived=False, **{
                    field: getattr(self, field) for field in self._extra_grouping_fields
                })
            else:  # Content Model
                content_obj = obj
            status = content_indicator(content_obj)
            menu = content_indicator_menu(
                request,
                status,
                content_obj._version,
                back=request.path_info + "?" + request.GET.urlencode(),
            ) if status else None
            return render_to_string(
                "admin/djangocms_versioning/indicator.html",
                {
                    "state": status or "empty",
                    "description": indicator_description.get(status, _("Empty")),
                    "menu_template": "admin/cms/page/tree/indicator_menu.html",
                    "menu": json.dumps(render_to_string("admin/cms/page/tree/indicator_menu.html",
                                                        dict(indicator_menu_items=menu))) if menu else None,
                }
            )
        indicator.short_description = self.indicator_column_label
        return indicator

    def indicator(self, obj):
        raise ValueError(
            "ModelAdmin.display_list contains \"indicator\" as a placeholder for status indicators. "
            "Status indicators, however, are not loaded. If you implement \"get_list_display\" make "
            "sure it calls super().get_list_display."
        )  # pragma: no cover

    def get_list_display(self, request):
        """Default behavior: replaces the text "indicator" by the indicator column"""
        if versionables.exists_for_content(self.model) or versionables.exists_for_grouper(self.model):
            return tuple(self.get_indicator_column(request) if item == "indicator" else item
                    for item in super().get_list_display(request))
        else:
            # remove "indicator" entry
            return tuple(item for item in super().get_list_display(request) if item != "indicator")
