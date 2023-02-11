from django.contrib.auth import get_permission_codename
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _

from djangocms_versioning.constants import (
    ARCHIVED,
    DRAFT,
    PUBLISHED,
    UNPUBLISHED,
    VERSION_STATES,
)
from djangocms_versioning.helpers import version_list_url
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


def content_indicator_menu(request, status, versions):
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
                _reverse_action(versions[0], "discard", back=request.path_info),
                "",  # Let view ask for confirmation
            ))
        if len(versions) >= 2 and versions[0].state == DRAFT and versions[1].state == PUBLISHED:
            menu.append((
                _("Compare Draft to Published..."), "cms-icon-layers",
                _reverse_action(versions[1], "compare") +
                "?" + urlencode(dict(
                    compare_to=versions[0].pk,
                    back=request.path_info,
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
        return None
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
