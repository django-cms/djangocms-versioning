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


class IndicatorStatusMixin:
    # Step 1:  The legend
    @property
    def indicator_descriptions(self):
        return {
            "published": _("Published"),
            "dirty": _("Changed"),
            "draft": _("Draft"),
            "unpublished": _("Unpublished"),
            "archived": _("Archived"),
            "empty": _("Empty"),
        }

    @classmethod
    def get_indicator_menu(cls, request, page_content):
        menu_template = "admin/cms/page/tree/indicator_menu.html"
        status = page_content.content_indicator()
        if not status or status == "empty":
            return super().get_indicator_menu(request, page_content)
        versions = page_content._version  # Cache from .content_indicator() (see mixin above)
        user = request.user
        menu = []
        if user.has_perm(f"cms.{get_permission_codename('change', versions[0]._meta)}"):
            if versions[0].check_publish.as_bool(user):
                menu.append((
                    _("Publish"), "cms-icon-publish",
                    reverse("admin:djangocms_versioning_pagecontentversion_publish", args=(versions[0].pk,)),
                    "js-cms-tree-lang-trigger",  # Triggers POST from the frontend
                ))
            if versions[0].check_edit_redirect.as_bool(user) and versions[0].state == PUBLISHED:
                menu.append((
                    _("Create new draft"), "cms-icon-edit-new",
                    reverse("admin:djangocms_versioning_pagecontentversion_edit_redirect", args=(versions[0].pk,)),
                    "js-cms-tree-lang-trigger js-cms-pagetree-page-view",  # Triggers POST from the frontend
                ))
            if versions[0].check_revert.as_bool(user) and versions[0].state == UNPUBLISHED:
                # Do not offer revert from unpublish -> archived versions to be managed in version admin
                label = _("Revert from Unpublish")
                menu.append((
                    label, "cms-icon-undo",
                    reverse("admin:djangocms_versioning_pagecontentversion_revert", args=(versions[0].pk,)),
                    "js-cms-tree-lang-trigger",  # Triggers POST from the frontend
                ))
            if versions[0].check_unpublish.as_bool(user):
                menu.append((
                    _("Unpublish"), "cms-icon-unpublish",
                    reverse("admin:djangocms_versioning_pagecontentversion_unpublish", args=(versions[0].pk,)),
                    "js-cms-tree-lang-trigger",
                ))
            if len(versions) > 1 and versions[1].check_unpublish.as_bool(user):
                menu.append((
                    _("Unpublish"), "cms-icon-unpublish",
                    reverse("admin:djangocms_versioning_pagecontentversion_unpublish", args=(versions[1].pk,)),
                    "js-cms-tree-lang-trigger",
                ))
            if versions[0].check_discard.as_bool(user):
                menu.append((
                    _("Delete Draft") if status == DRAFT else _("Delete Changes"), "cms-icon-bin",
                    reverse("admin:djangocms_versioning_pagecontentversion_discard", args=(versions[0].pk,)),
                    "",  # Let view ask for confirmation
                ))
            if len(versions) >= 2 and versions[0].state == DRAFT and versions[1].state == PUBLISHED:
                menu.append((
                    _("Compare Draft to Published..."), "cms-icon-compare",
                    reverse("admin:djangocms_versioning_pagecontentversion_compare", args=(versions[1].pk,)) +
                    "?" + urlencode(dict(
                        compare_to=versions[0].pk,
                        back=reverse("admin:cms_page_changelist"),
                    )),
                    "",
                ))
        menu.append(
            (
                _("Manage Versions..."), "cms-icon-manage-versions",
                version_list_url(versions[0].content),
                "",
            )
        )
        return menu_template if menu else "", menu


def content_indicator(page_content):
    """Translates available versions into status to be reflected by the indicator.
    Function caches the result in the page_content object"""

    if not hasattr(page_content, "_indicator_status"):
        versions = Version.objects.filter_by_content_grouping_values(
            page_content
        ).order_by("-pk")
        signature = {
            state: versions.filter(state=state)
            for state, name in VERSION_STATES
        }
        if signature[DRAFT] and not signature[PUBLISHED]:
            page_content._indicator_status = "draft"
            page_content._version = signature[DRAFT]
        elif signature[DRAFT] and signature[PUBLISHED]:
            page_content._indicator_status = "dirty"
            page_content._version = (signature[DRAFT][0], signature[PUBLISHED][0])
        elif signature[PUBLISHED]:
            page_content._indicator_status = "published"
            page_content._version = signature[PUBLISHED]
        elif signature[UNPUBLISHED]:
            page_content._indicator_status = "unpublished"
            page_content._version = signature[UNPUBLISHED]
        elif signature[ARCHIVED]:
            page_content._indicator_status = "archived"
            page_content._version = signature[ARCHIVED]
        else:
            page_content._indicator_status = None
            page_content._version = [None]
    return page_content._indicator_status


# Step 4: Check if current version is editable
def is_editable(page_content, request):
    if not page_content.content_indicator():
        # Something's wrong: content indicator not identified. Maybe no version?
        return False
    versions = page_content._version
    return versions[0].check_modify.as_bool(request.user)
