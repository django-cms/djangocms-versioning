from django.contrib.auth import get_permission_codename
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from cms.templatetags import cms_admin

from djangocms_versioning.constants import (
    ARCHIVED,
    DRAFT,
    PUBLISHED,
    UNPUBLISHED,
    VERSION_STATES,
)
from djangocms_versioning.helpers import version_list_url
from djangocms_versioning.models import Version


if hasattr(cms_admin, "TreePublishRow") and hasattr(cms_admin, "TreePublishRowMenu"):
    """djangocms-versioning defines its own indicator statuses. The two statuses of the
    core are fully replaced"""

    # Step 1:  The legend
    def _get_indicator_legend(self, context, page, language):
        return (
            (
                "cms-pagetree-node-state cms-pagetree-node-state-published",
                _("Published"),
            ),
            ("cms-pagetree-node-state cms-pagetree-node-state-dirty", _("Changed")),
            (
                "cms-pagetree-node-state cms-pagetree-node-state-unpublished",
                _("Unpublished"),
            ),
            ("cms-pagetree-node-state cms-pagetree-node-state-empty", _("Empty")),
        )

    cms_admin.TreePublishRow.get_indicator_legend = _get_indicator_legend

    def get_indicator_status(page_content):
        """Translates available versions into status to be reflected by the indicator.
        Function caches the result in the page_content object"""

        if page_content:
            if not hasattr(page_content, "_indicator_status"):
                versions = Version.objects.filter_by_content_grouping_values(
                    page_content
                )
                signature = {
                    state: versions.filter(state=state).exists()
                    for state, name in VERSION_STATES
                }
                if signature[DRAFT] and not signature[PUBLISHED]:
                    page_content._indicator_status = DRAFT
                    page_content._version = (
                        versions.filter(state=DRAFT).order_by("-pk").first()
                    )
                elif signature[DRAFT] and signature[PUBLISHED]:
                    page_content._indicator_status = "changed"
                    page_content._version = (
                        versions.filter(state=DRAFT).order_by("-pk").first()
                    )
                elif signature[PUBLISHED]:
                    page_content._indicator_status = PUBLISHED
                    page_content._version = versions.get(state=PUBLISHED)
                elif signature[UNPUBLISHED]:
                    page_content._indicator_status = UNPUBLISHED
                    page_content._version = (
                        versions.filter(state=UNPUBLISHED).order_by("-pk").first()
                    )
                elif not any(signature.values()):
                    page_content._indicator_status = ARCHIVED
                    page_content._version = (
                        versions.filter(state=ARCHIVED).order_by("-pk").first()
                    )
                else:
                    page_content._indicator_status = None
                    page_content._version = None
            return page_content._indicator_status, page_content._version
        return None, None

    # Step 2:  Individual indicators
    def _get_indicator(self, context, page, language):
        page_content = page.title_cache.get(language)
        status, version = get_indicator_status(page_content)
        if status == PUBLISHED:
            return (
                "cms-pagetree-node-state cms-pagetree-node-state-published published",
                _("Published"),
            )
        elif status == "changed":
            return "cms-pagetree-node-state cms-pagetree-node-state-dirty dirty", _(
                "Unpublished changes"
            )
        elif status == UNPUBLISHED:
            return (
                "cms-pagetree-node-state cms-pagetree-node-state-unpublished unpublished",
                _("Unpublished"),
            )
        elif status == DRAFT:
            return (
                "cms-pagetree-node-state cms-pagetree-node-state-unpublished unpublished",
                _("Draft"),
            )
        else:
            return "cms-pagetree-node-state cms-pagetree-node-state-empty empty", _(
                "Empty"
            )

    cms_admin.TreePublishRow.get_indicator = _get_indicator

    # Step 3:  Dropdown menu
    def indicator_patch(func):
        def _get_indicator_menu(self, context, page, language):
            page_content = page.title_cache.get(language)
            status, version = get_indicator_status(page_content)
            if status is None or version is None:
                return func(self, context, page, language)
            menu = []
            if context["request"].user.has_perm(
                "cms.{codename}".format(
                    codename=get_permission_codename("change", version._meta),
                )
            ):
                if status == DRAFT or status == "changed":
                    menu.append(
                        (
                            _("Publish"),
                            "cms-icon-check-o",
                            reverse(
                                "admin:djangocms_versioning_pagecontentversion_publish",
                                args=(version.pk,),
                            ),
                            "js-cms-tree-lang-trigger",  # Triggers POST from the frontend
                        )
                    )
                if status == UNPUBLISHED:
                    menu.append(
                        (
                            _("Revert from unpublish"),
                            "cms-icon-check-o",
                            reverse(
                                "admin:djangocms_versioning_pagecontentversion_revert",
                                args=(version.pk,),
                            ),
                            "js-cms-tree-lang-trigger",  # Triggers POST from the frontend
                        )
                    )
                if status == PUBLISHED or status == "changed":
                    menu.append(
                        (
                            _("Unpublish"),
                            "cms-icon-forbidden",
                            reverse(
                                "admin:djangocms_versioning_pagecontentversion_unpublish",
                                args=(version.pk,),
                            ),
                            "js-cms-tree-lang-trigger",
                        )
                    )
                menu.append(
                    (
                        _("Manage versions..."),
                        "cms-icon-copy",
                        version_list_url(version.content),
                        "",
                    )
                )
            return self.menu_template if menu else "", menu

        return _get_indicator_menu

    cms_admin.TreePublishRowMenu.get_indicator_menu = indicator_patch(
        cms_admin.TreePublishRowMenu.get_indicator_menu
    )
