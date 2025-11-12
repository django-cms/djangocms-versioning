from __future__ import annotations

from collections import OrderedDict
from copy import copy

from cms import __version__ as cms_version
from cms.cms_toolbars import (
    ADD_PAGE_LANGUAGE_BREAK,
    LANGUAGE_MENU_IDENTIFIER,
    BasicToolbar,
    PageToolbar,
    PlaceholderToolbar,
)
from cms.constants import REFRESH_PAGE
from cms.models import PageContent
from cms.toolbar.items import RIGHT, Break, ButtonList, TemplateItem
from cms.toolbar.utils import get_object_preview_url
from cms.toolbar_pool import toolbar_pool
from cms.utils import page_permissions
from cms.utils.conf import get_cms_setting
from cms.utils.i18n import get_language_dict, get_language_tuple
from cms.utils.urlutils import add_url_parameters, admin_reverse
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_permission_codename
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from packaging import version

from djangocms_versioning.conf import ALLOW_DELETING_VERSIONS, LOCK_VERSIONS
from djangocms_versioning.constants import DRAFT
from djangocms_versioning.helpers import (
    get_latest_admin_viewable_content,
    version_list_url,
)
from djangocms_versioning.models import Version

VERSIONING_MENU_IDENTIFIER = "version"
CMS_SUPPORTS_DELETING_TRANSLATIONS = version.Version(cms_version) > version.Version("4.1.4")
CMS_ADDS_PREVIEW_BUTTON = version.Version(cms_version) >= version.Version("4.2")


class VersioningToolbar(PlaceholderToolbar):
    def _get_versionable(self):
        """Helper method to get the versionable for the content type
        of the version
        """
        versioning_extension = apps.get_app_config("djangocms_versioning").cms_extension
        return versioning_extension.versionables_by_content[self.toolbar.obj.__class__]

    def _is_versioned(self):
        """Helper method to check if the model has been registered for
        versioning
        """
        versioning_extension = apps.get_app_config("djangocms_versioning").cms_extension
        return versioning_extension.is_content_model_versioned(self.toolbar.obj.__class__)

    def _get_proxy_model(self):
        """Helper method to get the proxy model class for the content
        model class
        """
        return self._get_versionable().version_model_proxy

    def _add_publish_button(self):
        """Helper method to add a publish button to the toolbar"""
        # Check if object is registered with versioning otherwise don't add
        if not self._is_versioned():
            return
        # Add the publish button if in edit mode
        if self.toolbar.edit_mode_active:
            item = ButtonList(side=self.toolbar.RIGHT)
            proxy_model = self._get_proxy_model()
            version = Version.objects.get_for_content(self.toolbar.obj)
            publish_url = reverse(
                f"admin:{proxy_model._meta.app_label}_{proxy_model.__name__.lower()}_publish",
                args=(version.pk,),
            )
            item.add_button(
                _("Publish"),
                url=publish_url,
                disabled=False,
                extra_classes=["cms-btn-action", "cms-form-post-method", "cms-versioning-js-publish-btn"],
            )
            self.toolbar.add_item(item)

    def add_edit_button(self):
        """
        Only override the CMS versioning button when the object is versionable
        """
        if not self._is_versioned():
            # Show the standard cms edit button for non versionable objects
            return super().add_edit_button()
        self._add_edit_button()
        self._add_unlock_button()

    def _add_edit_button(self, disabled=False):
        """Helper method to add an edit button to the toolbar"""
        item = ButtonList(side=self.toolbar.RIGHT)
        proxy_model = self._get_proxy_model()
        version = Version.objects.get_for_content(self.toolbar.obj)
        if version.check_edit_redirect.as_bool(self.request.user):
            edit_url = reverse(
                f"admin:{proxy_model._meta.app_label}_{proxy_model.__name__.lower()}_edit_redirect",
                args=(version.pk,),
            )
            pks_for_grouper = version.versionable.for_content_grouping_values(version.content).values_list(
                "pk", flat=True
            )
            content_type = ContentType.objects.get_for_model(version.content)
            draft_exists = Version.objects.filter(
                object_id__in=pks_for_grouper, content_type=content_type, state=DRAFT
            ).exists()
            item.add_button(
                _("Edit") if draft_exists else _("New Draft"),
                url=edit_url,
                disabled=disabled,
                extra_classes=["cms-btn-action", "cms-form-post-method", "cms-versioning-js-edit-btn"],
            )
            self.toolbar.add_item(item)

    def _add_unlock_button(self):
        """Helper method to add an edit button to the toolbar"""
        if LOCK_VERSIONS and self._is_versioned():
            item = ButtonList(side=self.toolbar.RIGHT)
            proxy_model = self._get_proxy_model()
            version = Version.objects.filter_by_content_grouping_values(self.toolbar.obj).filter(state=DRAFT).first()
            if version and version.check_unlock.as_bool(self.request.user):
                unlock_url = reverse(
                    f"admin:{proxy_model._meta.app_label}_{proxy_model.__name__.lower()}_unlock",
                    args=(version.pk,),
                )
                can_unlock = self.request.user.has_perm(f"{version._meta.app_label}.delete_versionlock")
                if can_unlock:
                    extra_classes = [
                        "cms-btn-action",
                        "cms-form-post-method",
                        "cms-versioning-js-unlock-btn",
                    ]
                else:
                    extra_classes = ["cms-versioning-js-unlock-btn"]
                item.add_button(
                    _("Unlock"),
                    url=unlock_url if can_unlock else "#",
                    disabled=not can_unlock,
                    extra_classes=extra_classes,
                )
                self.toolbar.add_item(item)

    def _add_lock_message(self):
        if self._is_versioned() and LOCK_VERSIONS and not self.toolbar.edit_mode_active:
            version = Version.objects.get_for_content(self.toolbar.obj)
            lock_message = TemplateItem(
                template="djangocms_versioning/admin/lock_indicator.html",
                extra_context={"version": version},
                side=RIGHT,
            )
            self.toolbar.add_item(lock_message, position=0)

    def _add_revert_button(self, disabled=False):
        """Helper method to add a revert button to the toolbar"""
        # Check if object is registered with versioning otherwise don't add
        if not self._is_versioned():
            return
        item = ButtonList(side=self.toolbar.RIGHT)
        proxy_model = self._get_proxy_model()
        version = Version.objects.get_for_content(self.toolbar.obj)
        if version.check_revert.as_bool(self.request.user):
            revert_url = reverse(
                f"admin:{proxy_model._meta.app_label}_{proxy_model._meta.model_name}_revert",
                args=(version.pk,),
            )
            item.add_button(
                _("Revert"),
                url=revert_url,
                disabled=disabled,
                extra_classes=["cms-btn-action"],
            )
            self.toolbar.add_item(item)

    def _add_versioning_menu(self):
        """Helper method to add version menu in the toolbar"""
        # Check if object is registered with versioning otherwise don't add
        if not self._is_versioned():
            return

        version = Version.objects.get_for_content(self.toolbar.obj)
        if version is None:
            return

        version_menu_label = version.short_name()
        versioning_menu = self.toolbar.get_or_create_menu(
            VERSIONING_MENU_IDENTIFIER, version_menu_label, disabled=False
        )
        version = version.convert_to_proxy()
        if self.request.user.has_perm(
            "{app_label}.{codename}".format(
                app_label=version._meta.app_label,
                codename=get_permission_codename("change", version._meta),
            )
        ):
            url = version_list_url(version.content)
            versioning_menu.add_sideframe_item(_("Manage Versions"), url=url)
            # Compare to source menu entry
            if version.source:
                name = _("Compare to {source}").format(source=_(version.source.short_name()))
                proxy_model = self._get_proxy_model()
                url = reverse(
                    f"admin:{proxy_model._meta.app_label}_{proxy_model.__name__.lower()}_compare",
                    args=(version.source.pk,),
                )

                url += "?" + urlencode(
                    {
                        "compare_to": version.pk,
                        "back": self.toolbar.request_path,
                    }
                )
                versioning_menu.add_link_item(name, url=url)
                # Discard changes menu entry (wrt to source)
                if version.check_discard.as_bool(self.request.user):  # pragma: no cover
                    versioning_menu.add_item(Break())
                    versioning_menu.add_link_item(
                        _("Discard Changes"),
                        url=reverse(
                            f"admin:{proxy_model._meta.app_label}_{proxy_model.__name__.lower()}_discard",
                            args=(version.pk,),
                        ),
                    )

    def _get_published_page_version(self):
        """Returns a published page if one exists for the toolbar object"""
        language = self.current_lang

        # Exit the current toolbar object is not a Page / PageContent instance
        if not isinstance(self.toolbar.obj, PageContent) or not self.page:
            return

        return PageContent.objects.filter(page=self.page, language=language).select_related("page").first()

    def _add_view_published_button(self):
        """Helper method to add a publish button to the toolbar"""
        # Check if object is registered with versioning otherwise don't add
        if not self._is_versioned():
            return

        # Add the View published button if in edit or preview mode
        published_version = self._get_published_page_version()
        if not published_version:
            return

        url = published_version.get_absolute_url() if hasattr(published_version, "get_absolute_url") else None
        if url and (self.toolbar.edit_mode_active or self.toolbar.preview_mode_active):
            item = ButtonList(side=self.toolbar.RIGHT)
            item.add_button(
                _("View Published"),
                url=url,
                disabled=False,
                extra_classes=["cms-btn", "cms-btn-switch-save"],
            )
            self.toolbar.add_item(item)

    def _add_preview_button(self):
        """Helper method to add a preview button to the toolbar when not in preview mode"""
        # Check if object is registered with versioning otherwise don't add
        if not self._is_versioned() or CMS_ADDS_PREVIEW_BUTTON:
            return

        if not self.toolbar.preview_mode_active and not self.toolbar.edit_mode_active:
            # Any mode not preview mode can have a preview button
            # Exclude edit mode, however, since the django CMS core already ads the preview button for edit mode
            self.add_preview_button()

    def post_template_populate(self):
        super().post_template_populate()
        self._add_lock_message()
        self._add_preview_button()
        self._add_view_published_button()
        self._add_revert_button()
        self._add_publish_button()
        self._add_versioning_menu()


class VersioningPageToolbar(PageToolbar):
    """
    Overriding the original Page toolbar to ensure that draft and published pages
    can be accessed and to allow full control over the Page toolbar for versioned pages.
    """

    def __init__(self, *args, **kwargs):
        self.page_content: PageContent | None = None
        super().__init__(*args, **kwargs)

    def get_page_content(self, language: str | None = None) -> PageContent:
        # This method overwrites the method in django CMS core. Not necessary
        # for django CMS 4.2+
        if not language:
            language = self.current_lang

        if isinstance(self.page_content, PageContent) and self.page_content.language == language:
            # Already known - no need to query it again
            return self.page_content
        toolbar_obj = self.toolbar.get_object()
        if isinstance(toolbar_obj, PageContent) and toolbar_obj.language == language:
            # Already in the toolbar, then use it!
            return toolbar_obj
        else:
            # Get it from the DB
            return get_latest_admin_viewable_content(self.page, language=language, include_unpublished_archived=True)

    def populate(self):
        self.page = self.request.current_page
        self.page_content = self.get_page_content() if self.page else None
        self.permissions_activated = get_cms_setting("PERMISSION")

        self.change_admin_menu()
        self.add_page_menu()
        self.change_language_menu()

    def override_language_menu(self):
        """
        Override the default language menu for pages that are versioned.
        The default language menu is too generic so for pages we need to replace it.
        """
        # Only override the menu if it exists and a page can be found
        language_menu = self.toolbar.get_menu(LANGUAGE_MENU_IDENTIFIER, _("Language"))
        if settings.USE_I18N and language_menu and self.page:
            # remove_item uses `items` attribute, so we have to copy object
            for _item in copy(language_menu.items):
                language_menu.remove_item(item=_item)

            for code, name in get_language_tuple(self.current_site.pk):
                # Get the page content, it could be draft too!
                page_content = self.page.get_admin_content(language=code)
                if page_content:
                    url = get_object_preview_url(page_content, code)
                    language_menu.add_link_item(name, url=url, active=self.current_lang == code)

    def change_language_menu(self):
        can_change = (
            self.page
            and page_permissions.user_can_change_page(
                user=self.request.user, page=self.page, site=self.current_site
            )
        )

        if can_change:
            language_menu = self.toolbar.get_menu(LANGUAGE_MENU_IDENTIFIER)
            if not language_menu:
                return None

            languages = get_language_dict(self.current_site.pk)
            remove = [(code, languages.get(code, code)) for code in self.page.get_languages() if code in languages]
            add = [code for code in languages.items() if code not in remove]
            copy = [
                (code, name) for code, name in languages.items() if code != self.current_lang and (code, name) in remove
            ]

            # ADD TRANSLATION — only if user has change permission
            if add:
                language_menu.add_break(ADD_PAGE_LANGUAGE_BREAK)

                add_plugins_menu = language_menu.get_or_create_menu(f"{LANGUAGE_MENU_IDENTIFIER}-add", _("Add Translation"))  # noqa: E501

                page_add_url = admin_reverse("cms_pagecontent_add")

                for code, name in add:
                    url = add_url_parameters(page_add_url, cms_page=self.page.pk, language=code)
                    add_plugins_menu.add_modal_item(name, url=url)

            # DELETE TRANSLATION — only if user has change permission
            if remove and ALLOW_DELETING_VERSIONS and CMS_SUPPORTS_DELETING_TRANSLATIONS:
                remove_plugins_menu = language_menu.get_or_create_menu(
                    f"{LANGUAGE_MENU_IDENTIFIER}-del", _("Delete Translation")
                )
                disabled = len(remove) == 1
                for code, name in remove:
                    pagecontent = self.page.get_admin_content(language=code)
                    if pagecontent:
                        translation_delete_url = admin_reverse("cms_pagecontent_delete", args=(pagecontent.pk,))
                        url = add_url_parameters(translation_delete_url, language=code)
                        on_close = REFRESH_PAGE
                        if self.toolbar.get_object() == pagecontent and not disabled:
                            other_content = next(
                                (
                                    self.page.get_admin_content(lang)
                                    for lang in self.page.get_languages()
                                    if lang != pagecontent.language and lang in languages
                                ),
                                None,
                            )
                            on_close = get_object_preview_url(other_content)
                        remove_plugins_menu.add_modal_item(name, url=url, disabled=disabled, on_close=on_close)
            # COPY ALL PLUGINS — only if user can change AND in edit mode
            if self.toolbar.edit_mode_active and copy:
                copy_plugins_menu = language_menu.get_or_create_menu(
                    f"{LANGUAGE_MENU_IDENTIFIER}-copy", _("Copy all plugins")
                )
                title = _("from %s")
                question = _("Are you sure you want to copy all plugins from %s?")
                item_added = False
                for code, name in copy:
                    # Get the Draft or Published PageContent.
                    page_content = self.page.get_admin_content(language=code)
                    if page_content:  # Only offer to copy if content for source language exists
                        page_copy_url = admin_reverse("cms_pagecontent_copy_language", args=(page_content.pk,))
                        copy_plugins_menu.add_ajax_item(
                            title % name,
                            action=page_copy_url,
                            data={"source_language": code, "target_language": self.current_lang},
                            question=question % name,
                            on_success=self.toolbar.REFRESH_PAGE,
                        )
                        item_added = True
                    if not item_added:  # pragma: no cover
                        copy_plugins_menu.add_link_item(
                            _("No other language available"),
                            url="#",
                            disabled=True,
                        )


class VersioningBasicToolbar(BasicToolbar):
    def add_language_menu(self):
        """
        Originally did override the default language menu for pages that are versioned.
        Now creates the menu from scratch, since VersiongBasicToolbar prevents the
        core from creating the too generic default language menu.
        """
        if not settings.USE_I18N or not self.request.current_page:
            # Only add if no page is shown
            super().add_language_menu()
            return

        languages = get_language_tuple(self.current_site.pk)
        if len(languages) < 2:
            return  # No need to show the language menu if there is only one language

        language_menu = self.toolbar.get_or_create_menu(
            LANGUAGE_MENU_IDENTIFIER, _("Language"), position=-1
        )
        for code, name in languages:
            # Get the page content, it could be draft too!
            page_content = self.page.get_admin_content(language=code)
            if page_content:
                url = get_object_preview_url(page_content, code)
                language_menu.add_link_item(name, url=url, active=self.current_lang == code)


def replace_toolbar(old, new):
    """Replace `old` toolbar class with `new` class, while keeping its position in toolbar_pool."""
    new_name = ".".join((new.__module__, new.__name__))
    old_name = ".".join((old.__module__, old.__name__))
    toolbar_pool.toolbars = OrderedDict(
        (new_name, new) if name == old_name else (name, toolbar) for name, toolbar in toolbar_pool.toolbars.items()
    )


replace_toolbar(PageToolbar, VersioningPageToolbar)
replace_toolbar(PlaceholderToolbar, VersioningToolbar)
replace_toolbar(BasicToolbar, VersioningBasicToolbar)
