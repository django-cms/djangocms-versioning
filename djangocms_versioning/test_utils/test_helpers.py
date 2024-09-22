from cms.toolbar.items import ButtonList
from cms.toolbar.toolbar import CMSToolbar
from django.test import RequestFactory

from djangocms_versioning.cms_toolbars import VersioningToolbar
from djangocms_versioning.test_utils.factories import UserFactory


def get_toolbar(content_obj, user=None, **kwargs):
    """
    Helper method to set up the toolbar

    Warning: Other apps may use this helper to improve readability and stability of tests.
            Be sure to keep backwards compatibility where possible
    """
    # Set the user if none are sent
    if not user:
        user = UserFactory(is_staff=True)

    request = kwargs.get("request", RequestFactory().get("/"))
    request.user = user
    request.session = kwargs.get("session", {})
    request.current_page = kwargs.get("current_page", getattr(content_obj, "page", None))
    request.toolbar = CMSToolbar(request)
    # Set the toolbar class
    if kwargs.get("toolbar_class", False):
        toolbar_class = kwargs.get("toolbar_class")
    else:
        toolbar_class = VersioningToolbar
    toolbar = toolbar_class(
        request, toolbar=request.toolbar, is_current_app=True, app_path="/"
    )
    toolbar.toolbar.set_object(content_obj)
    # Set the toolbar mode
    if kwargs.get("edit_mode", False):
        toolbar.toolbar.edit_mode_active = True
        toolbar.toolbar.preview_mode_active = False
        toolbar.toolbar.structure_mode_active = False
    elif kwargs.get("preview_mode", False):
        toolbar.toolbar.edit_mode_active = False
        toolbar.toolbar.preview_mode_active = True
        toolbar.toolbar.structure_mode_active = False
    elif kwargs.get("structure_mode", False):
        toolbar.toolbar.edit_mode_active = False
        toolbar.toolbar.preview_mode_active = False
        toolbar.toolbar.structure_mode_active = True
    toolbar.populate()
    return toolbar


def find_toolbar_buttons(button_name, toolbar):
    """
    Returns a button that matches the button name

    Warning: Other apps may use this helper to improve readability and stability of tests.
        Be sure to keep backwards compatibility where possible
    """
    found = []
    for button_list in toolbar.get_right_items():
        if isinstance(button_list, ButtonList):
            found = found + [
                button for button in button_list.buttons if button.name == button_name
            ]
    return found


def toolbar_button_exists(button_name, toolbar):
    """
    Check to see if a button exists in a supplied toolbar

    Warning: Other apps may use this helper to improve readability and stability of tests.
        Be sure to keep backwards compatibility where possible
    """
    found = find_toolbar_buttons(button_name, toolbar)
    return bool(len(found))
