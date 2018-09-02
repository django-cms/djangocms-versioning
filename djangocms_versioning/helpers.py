import warnings
from contextlib import contextmanager

from django.contrib import admin
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType

from .admin import VersionAdmin, VersioningAdminMixin
from .managers import PublishedContentManagerMixin
from .models import Version


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


def register_versionadmin_proxy(versionable, admin_site=None):
    """Creates a model admin class based on `VersionAdmin` and registers
    it with `admin_site` for `versionable.version_model_proxy`.

    This model class applies filtering on the list of versions,
    so that only versions for `versionable.content_model` are shown.

    :param versionable: VersionableItem instance
    :param admin_site: AdminSite instance
    """
    if admin_site is None:
        admin_site = admin.site

    if versionable.version_model_proxy in admin_site._registry:
        # Attempting to register the proxy again is a no-op.
        warnings.warn(
            '{!r} is already registered with admin.'.format(
                versionable.version_model_proxy,
            ),
            UserWarning,
        )
        return

    class ProxiedAdmin(VersionAdmin):

        def get_queryset(self, request):
            content_type = ContentType.objects.get_for_model(self.model._source_model)
            return super().get_queryset(request).filter(
                content_type=content_type,
            )
    ProxiedAdmin.__name__ = (
        versionable.grouper_model.__name__ +
        VersionAdmin.__name__
    )

    admin_site.register(versionable.version_model_proxy, ProxiedAdmin)


def published_content_manager_factory(manager):
    """A class factory returning manager class with overriden
    versioning functionality.

    :param manager: Existing manager class
    :return: A subclass of `PublishedContentManagerMixin` and `manager`
    """
    return type(
        'Published' + manager.__name__,
        (PublishedContentManagerMixin, manager),
        {'use_in_migrations': False},
    )


def replace_default_manager(model):
    if isinstance(model.objects, PublishedContentManagerMixin):
        return
    model.add_to_class('_original_manager', model.objects.__class__())
    manager = published_content_manager_factory(model.objects.__class__)()
    model._meta.local_managers = [
        manager for manager in model._meta.local_managers
        if manager.name != 'objects'
    ]
    model.add_to_class('objects', manager)


def inject_generic_relation_to_version(model):
    model.add_to_class('versions', GenericRelation(Version))


def _set_default_manager(model, manager):
    model._meta.local_managers = [
        m for m in model._meta.local_managers
        if m.name != 'objects'
    ]
    model.add_to_class('objects', manager)


@contextmanager
def override_default_manager(model, manager):
    original_manager = model.objects
    _set_default_manager(model, manager)
    yield
    _set_default_manager(model, original_manager)
