from collections import OrderedDict

from django.apps import apps
from django.contrib.auth import get_permission_codename
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from cms.cms_toolbars import PlaceholderToolbar
from cms.toolbar.items import ButtonList
from cms.toolbar_pool import toolbar_pool

from djangocms_versioning.models import Version

from .helpers import version_list_url


VERSIONING_MENU_IDENTIFIER = "version"


class VersioningToolbar(PlaceholderToolbar):
    class Media:
        js = ("djangocms_versioning/js/actions.js",)

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
        return versioning_extension.is_content_model_versioned(
            self.toolbar.obj.__class__
        )

    def _get_proxy_model(self):
        """Helper method to get the proxy model class for the content
        model class
        """
        return self._get_versionable().version_model_proxy

    def _add_publish_button(self):
        """Helper method to add a publish button to the toolbar
        """
        # Only add the publish button if the content type is registered
        # with versioning
        if not self._is_versioned():
            return
        # Add the publish button if in edit mode
        if self.toolbar.edit_mode_active:
            item = ButtonList(side=self.toolbar.RIGHT)
            proxy_model = self._get_proxy_model()
            version = Version.objects.get_for_content(self.toolbar.obj)
            publish_url = reverse(
                "admin:{app}_{model}_publish".format(
                    app=proxy_model._meta.app_label, model=proxy_model.__name__.lower()
                ),
                args=(version.pk,),
            )
            item.add_button(
                _("Publish"),
                url=publish_url,
                disabled=False,
                extra_classes=["cms-btn-action", "cms-versioning-js-publish-btn"],
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

    def _add_edit_button(self, disabled=False):
        """Helper method to add an edit button to the toolbar
        """
        item = ButtonList(side=self.toolbar.RIGHT)
        proxy_model = self._get_proxy_model()
        version = Version.objects.get_for_content(self.toolbar.obj)
        edit_url = reverse(
            "admin:{app}_{model}_edit_redirect".format(
                app=proxy_model._meta.app_label, model=proxy_model.__name__.lower()
            ),
            args=(version.pk,),
        )
        item.add_button(
            _("Edit"),
            url=edit_url,
            disabled=disabled,
            extra_classes=["cms-btn-action", "cms-versioning-js-edit-btn"],
        )
        self.toolbar.add_item(item)

    def _add_versioning_menu(self):
        """ Helper method to add version menu in the toolbar
        """
        # Check if object is registred with versioning otherwise dont add
        if not self._is_versioned():
            return

        version = Version.objects.get_for_content(self.toolbar.obj)
        if version is None:
            return

        version_menu_label = _("Version #{number} ({state})").format(
            number=version.number, state=version.state
        )
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

    def post_template_populate(self):
        super(VersioningToolbar, self).post_template_populate()
        self._add_publish_button()
        self._add_versioning_menu()


def replace_toolbar(old, new):
    """Replace `old` toolbar class with `new` class,
    while keeping its position in toolbar_pool.
    """
    new_name = ".".join((new.__module__, new.__name__))
    old_name = ".".join((old.__module__, old.__name__))
    toolbar_pool.toolbars = OrderedDict(
        [
            (new_name, new) if name == old_name else (name, toolbar)
            for name, toolbar in toolbar_pool.toolbars.items()
        ]
    )


replace_toolbar(PlaceholderToolbar, VersioningToolbar)
