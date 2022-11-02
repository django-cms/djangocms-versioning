from django.contrib.auth import get_permission_codename
from django.urls import NoReverseMatch, reverse
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
            ("cms-pagetree-node-state cms-pagetree-node-state-draft", _("Draft")),
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
                ).order_by("-pk")
                signature = {
                    state: versions.filter(state=state)
                    for state, name in VERSION_STATES
                }
                if signature[DRAFT] and not signature[PUBLISHED]:
                    page_content._indicator_status = DRAFT
                    page_content._version = signature[DRAFT]
                elif signature[DRAFT] and signature[PUBLISHED]:
                    page_content._indicator_status = "changed"
                    page_content._version = (signature[DRAFT][0], signature[PUBLISHED][0])
                elif signature[PUBLISHED]:
                    page_content._indicator_status = PUBLISHED
                    page_content._version = signature[PUBLISHED]
                elif signature[UNPUBLISHED]:
                    page_content._indicator_status = UNPUBLISHED
                    page_content._version = signature[UNPUBLISHED]
                elif not any(signature.values()):
                    page_content._indicator_status = ARCHIVED
                    page_content._version = signature[ARCHIVED]
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
            try:
                page.get_absolute_url(language=language, fallback=False)
                return (
                    "cms-pagetree-node-state cms-pagetree-node-state-published published",
                    _("Published"),
                )
            except NoReverseMatch:
                return (
                    "cms-pagetree-node-state cms-pagetree-node-state-unpublished-parent unpublished-parent",
                    _("Unpublished parent"),
                )
        elif status == "changed":
            return (
                "cms-pagetree-node-state cms-pagetree-node-state-dirty dirty",
                _("Unpublished changes"),
            )
        elif status == UNPUBLISHED:
            return (
                "cms-pagetree-node-state cms-pagetree-node-state-unpublished unpublished",
                _("Unpublished"),
            )
        elif status == DRAFT:
            return (
                "cms-pagetree-node-state cms-pagetree-node-state-draft draft",
                _("Draft"),
            )
        else:
            return (
                "cms-pagetree-node-state cms-pagetree-node-state-empty empty",
                _("Empty"),
            )

    cms_admin.TreePublishRow.get_indicator = _get_indicator

    # Step 3:  Dropdown menu
    def indicator_patch(func):
        def _get_indicator_menu(self, context, page, language):
            page_content = page.title_cache.get(language)
            status, versions = get_indicator_status(page_content)  # get status and most relevant versions
            if status is None or versions is None:
                return func(self, context, page, language)
            menu = []
            if context["request"].user.has_perm(
                "cms.{codename}".format(
                    codename=get_permission_codename("change", versions[0]._meta),
                )
            ):
                if status == DRAFT or status == "changed":
                    menu.append(
                        (
                            _("Publish"),
                            "cms-icon-check-o",
                            reverse(
                                "admin:djangocms_versioning_pagecontentversion_publish",
                                args=(versions[0].pk,),
                            ),
                            "js-cms-tree-lang-trigger",  # Triggers POST from the frontend
                        )
                    )
                if status == UNPUBLISHED:
                    menu.append(
                        (
                            _("Revert from Unpublish"),
                            "cms-icon-undo cms-icon-check-o",  # check-o: fallback for cms versions without undo icon
                            reverse(
                                "admin:djangocms_versioning_pagecontentversion_revert",
                                args=(versions[0].pk,),
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
                                args=(versions[0 if status == PUBLISHED else 1].pk,),
                            ),
                            "js-cms-tree-lang-trigger",
                        )
                    )
                if status == DRAFT or status == "changed":
                    menu.append(
                        (
                            _("Delete Draft") if status == DRAFT else _("Delete Changes"),
                            "cms-icon-bin",
                            reverse(
                                "admin:djangocms_versioning_pagecontentversion_discard",
                                args=(versions[0].pk,),
                            ),
                            "",  # Let view ask for confirmation
                        )
                    )
                menu.append(
                    (
                        _("Manage Versions..."),
                        "cms-icon-copy",
                        version_list_url(versions[0].content),
                        "",
                    )
                )
            return self.menu_template if menu else "", menu

        return _get_indicator_menu

    cms_admin.TreePublishRowMenu.get_indicator_menu = indicator_patch(
        cms_admin.TreePublishRowMenu.get_indicator_menu
    )

    # Step 4: Check if current version is editable
    def edit_patch(func):
        def _is_editable(self, context, page, language):
            if not func(self, context, page, language):
                return False
            page_content = page.title_cache.get(language)
            status, versions = get_indicator_status(page_content)  # get status and most relevant versions
            return versions[0].check_modify.as_bool(context["request"].user) if versions else True

        return _is_editable

    cms_admin.GetAdminUrlForLanguage.is_editable = edit_patch(
        cms_admin.GetAdminUrlForLanguage.is_editable
    )
