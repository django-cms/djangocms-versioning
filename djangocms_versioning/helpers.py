from django.contrib import admin
from django.contrib.contenttypes.models import ContentType

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


def register_versionadmin_proxy(version_proxy, grouper_name, admin_site=None):
    """
    ;param version_proxy: Proxy model to Version
    :param grouper_name: Grouper model name
    :param admin_site: AdminSite instance
    """
    if admin_site is None:
        admin_site = admin.site

    if version_proxy in admin_site._registry:
        # Attempting to register the proxy again is a no-op.
        return

    class ProxiedAdmin(VersionAdmin):

        def get_queryset(self, request):
            content_type = ContentType.objects.get_for_model(self.model._content_model)
            return super().get_queryset(request).filter(
                content_type=content_type,
            )
    ProxiedAdmin.__name__ = grouper_name + VersionAdmin.__name__

    admin_site.register(version_proxy, ProxiedAdmin)
