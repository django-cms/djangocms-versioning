from cms.utils.urlutils import admin_reverse
from django.contrib.auth import get_permission_codename
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _

from .constants import ARCHIVED, DRAFT, PUBLISHED, UNPUBLISHED, VERSION_STATES
from .models import Version


def _reverse_action(version, action, back=None):
    get_params = f"?{urlencode({'back': back})}" if back else ""
    return admin_reverse(
        f"{version._meta.app_label}_{version.versionable.version_model_proxy._meta.model_name}_{action}",
        args=(version.pk,)
    ) + get_params


def content_indicator_menu(request, status, versions, back=""):
    from djangocms_versioning.helpers import version_list_url

    menu = []
    if request.user.has_perm(f"cms.{get_permission_codename('change', versions[0]._meta)}"):
        if versions[0].check_unlock.as_bool(request.user):
            can_unlock = request.user.has_perm("djangocms_versioning.delete_versionlock")
            # disable if permissions are insufficient
            additional_class = "" if can_unlock else " cms-pagetree-dropdown-item-disabled"
            menu.append((
                _("Unlock (%(message)s)") % {"message": versions[0].locked_message()}, "cms-icon-unlock",
                _reverse_action(versions[0], "unlock"),
                "js-cms-tree-lang-trigger" + additional_class,  # Triggers POST from the frontend
            ))
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
                _("Delete Draft") if status == DRAFT else _("Discard Changes"), "cms-icon-bin",
                _reverse_action(versions[0], "discard", back=back),
                "",  # Let view ask for confirmation
            ))
        if len(versions) >= 2 and versions[0].state == DRAFT and versions[1].state == PUBLISHED:
            menu.append((
                _("Compare Draft to Published..."), "cms-icon-layers",
                _reverse_action(versions[1], "compare") +
                "?" + urlencode({
                    "compare_to": versions[0].pk,
                    "back": back,
                }),
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
        elif versions[0].state == UNPUBLISHED:
            content_obj._indicator_status = "unpublished"
            content_obj._version = signature[UNPUBLISHED]
        elif versions[0].state == ARCHIVED:
            content_obj._indicator_status = "archived"
            content_obj._version = signature[ARCHIVED]
        else:  # pragma: no cover
            content_obj._indicator_status = None
            content_obj._version = [None]
    return content_obj._indicator_status
