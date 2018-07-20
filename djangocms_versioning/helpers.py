from django.contrib import admin

from .admin import VersionAdmin, VersioningAdminMixin


def versioning_admin_factory(admin_class):
    """A class factory returning admin class with overriden
    versioning functionality.

    :param admin_class: Existing admin class
    :return: A subclass of `VersioningAdminMixin` and `admin_class`
    """
    return type('Versioned' + admin_class.__name__, (VersioningAdminMixin, admin_class), {})


def _replace_admin_for_model(modeladmin, admin_site):
    """Replaces existing admin class registered for `modeladmin.model` with
    a subclass that includes versioning functionality.

    Doesn't do anything if `modeladmin` is already an instance of
    `VersioningAdminMixin`.

    :param model: ModelAdmin instance
    :param admin_site: AdminSite instance
    """
    if isinstance(modeladmin, VersioningAdminMixin):
        return
    new_admin_class = versioning_admin_factory(modeladmin.__class__)
    admin_site.unregister(modeladmin.model)
    admin_site.register(modeladmin.model, new_admin_class)


def replace_admin_for_models(models, admin_site=None):
    """
    :param models: List of model classes
    :param admin_site: AdminSite instance
    """
    if admin_site is None:
        admin_site = admin.site
    for model in models:
        try:
            modeladmin = admin_site._registry[model]
        except KeyError:
            continue
        _replace_admin_for_model(modeladmin, admin_site)


def register_version_admin_for_models(models, admin_site=None):
    """
    :param models: List of model classes
    :param admin_site: AdminSite instance
    """
    if admin_site is None:
        admin_site = admin.site
    for model in models:
        if model not in admin_site._registry:
            admin_site.register(model, VersionAdmin)
