import copy
import warnings
from contextlib import contextmanager

from django.contrib import admin
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from cms.toolbar.utils import get_object_edit_url
from cms.utils.helpers import is_editable_model
from cms.utils.urlutils import add_url_parameters, admin_reverse

from .constants import DRAFT
from .managers import PublishedContentManagerMixin
from .versionables import _cms_extension


def versioning_admin_factory(admin_class):
    """A class factory returning admin class with overriden
    versioning functionality.

    :param admin_class: Existing admin class
    :return: A subclass of `VersioningAdminMixin` and `admin_class`
    """
    from .admin import VersioningAdminMixin
    return type('Versioned' + admin_class.__name__, (VersioningAdminMixin, admin_class), {})


def _replace_admin_for_model(modeladmin, admin_site):
    """Replaces existing admin class registered for `modeladmin.model` with
    a subclass that includes versioning functionality.

    Doesn't do anything if `modeladmin` is already an instance of
    `VersioningAdminMixin`.

    :param model: ModelAdmin instance
    :param admin_site: AdminSite instance
    """
    from .admin import VersioningAdminMixin
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
    from .admin import VersionAdmin

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

    class VersionProxyAdminMixin(VersionAdmin):

        def get_queryset(self, request):
            return super().get_queryset(request).filter(
                content_type__in=versionable.content_types,
            )

    ProxiedAdmin = type(
        versionable.grouper_model.__name__ + VersionAdmin.__name__,
        (VersionProxyAdminMixin, admin.ModelAdmin),
        {},
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
    original_manager = model.objects.__class__
    manager = published_content_manager_factory(original_manager)()
    model._meta.local_managers = [
        manager for manager in model._meta.local_managers
        if manager.name != 'objects'
    ]
    model.add_to_class('objects', manager)
    model.add_to_class('_original_manager', original_manager())


def inject_generic_relation_to_version(model):
    from .models import Version
    model.add_to_class('versions', GenericRelation(Version))


def _set_default_manager(model, manager):
    model._meta.local_managers = [
        m for m in model._meta.local_managers
        if m.name != 'objects'
    ]
    manager_ = copy.copy(manager)
    manager_.name = 'objects'
    model.add_to_class('objects', manager_)


@contextmanager
def override_default_manager(model, manager):
    original_manager = model.objects
    _set_default_manager(model, manager)
    yield
    _set_default_manager(model, original_manager)


def _version_list_url(versionable, **params):
    proxy = versionable.version_model_proxy
    return add_url_parameters(
        admin_reverse('{app}_{model}_changelist'.format(
            app=proxy._meta.app_label,
            model=proxy._meta.model_name,
        )),
        **params
    )


def version_list_url(content):
    """Returns a URL to list of content model versions,
    filtered by `content`'s grouper
    """
    versionable = _cms_extension().versionables_by_content[content.__class__]
    return _version_list_url(
        versionable,
        **versionable.grouping_values(content, relation_suffix=False)
    )


def version_list_url_for_grouper(grouper):
    """Returns a URL to list of content model versions,
    filtered by `grouper`
    """
    versionable = _cms_extension().versionables_by_grouper[grouper.__class__]
    return _version_list_url(versionable, **{
        versionable.grouper_field_name: str(grouper.pk)
    })


def is_content_editable(placeholder, user):
    """A helper method for monkey patch to check version is in edit state

    :param placeholder: current placeholder
    :param user: user object
    :return: Boolean
    """
    from .models import Version
    version = Version.objects.get_for_content(placeholder.source)
    return version.state == DRAFT


def get_editable_url(content_obj):
    """If the object is editable the cms editable view should be used, with the toolbar.
       This method is provides the URL for it.
    """
    if is_editable_model(content_obj.__class__):
        url = get_object_edit_url(content_obj)
    # Or else, the standard edit view should be used
    else:
        url = reverse('admin:{app}_{model}_change'.format(
            app=content_obj._meta.app_label,
            model=content_obj._meta.model_name,
        ), args=(content_obj.pk,))
    return url


# TODO Based on polymorphic.query_translate._get_mro_content_type_ids,
# can use that when polymorphic gets a new release
def get_content_types_with_subclasses(models, using=None):
    content_types = set()
    for model in models:
        content_type = ContentType.objects.db_manager(
            using,
        ).get_for_model(model, for_concrete_model=False)
        content_types.add(content_type.pk)
        subclasses = model.__subclasses__()
        if subclasses:
            content_types.update(
                get_content_types_with_subclasses(subclasses, using),
            )
    return content_types
