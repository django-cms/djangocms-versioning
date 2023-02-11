import copy
import warnings
from contextlib import contextmanager

from django.contrib import admin
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.sql.where import WhereNode
from django.urls import reverse

from cms.toolbar.utils import get_object_edit_url, get_object_preview_url
from cms.utils.helpers import is_editable_model
from cms.utils.urlutils import add_url_parameters, admin_reverse

from . import versionables
from .constants import DRAFT, PUBLISHED
from .versionables import _cms_extension


def versioning_admin_factory(admin_class, mixin):
    """A class factory returning admin class with overriden
    versioning functionality.

    :param admin_class: Existing admin class
    :param mixin: Mixin class
    :return: A subclass of `VersioningAdminMixin` and `admin_class`
    """
    return type("Versioned" + admin_class.__name__, (mixin, admin_class), {})


def _replace_admin_for_model(modeladmin, mixin, admin_site):
    """Replaces existing admin class registered for `modeladmin.model` with
    a subclass that includes versioning functionality.

    Doesn't do anything if `modeladmin` is already an instance of
    `mixin`.

    :param model: ModelAdmin instance
    :param mixin: Mixin class
    :param admin_site: AdminSite instance
    """
    if isinstance(modeladmin, mixin):
        return
    new_admin_class = versioning_admin_factory(modeladmin.__class__, mixin)
    admin_site.unregister(modeladmin.model)
    admin_site.register(modeladmin.model, new_admin_class)


def replace_admin_for_models(pairs, admin_site=None):
    """
    :param models: List of (model class, admin mixin class) tuples
    :param admin_site: AdminSite instance
    """
    if admin_site is None:
        admin_site = admin.site
    for model, mixin in pairs:
        try:
            modeladmin = admin_site._registry[model]
        except KeyError:
            continue
        _replace_admin_for_model(modeladmin, mixin, admin_site)


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
            "{!r} is already registered with admin.".format(
                versionable.version_model_proxy
            ),
            UserWarning,
        )
        return

    class VersionProxyAdminMixin(VersionAdmin):
        def get_queryset(self, request):
            return (
                super()
                .get_queryset(request)
                .filter(content_type__in=versionable.content_types)
            )

    ProxiedAdmin = type(
        versionable.grouper_model.__name__ + VersionAdmin.__name__,
        (VersionProxyAdminMixin, admin.ModelAdmin),
        {},
    )

    admin_site.register(versionable.version_model_proxy, ProxiedAdmin)


def manager_factory(manager, prefix, mixin):
    """A class factory returning a manager class with an added mixin to override for
    versioning functionality.

    :param manager: Existing manager class
    :return: A subclass of `PublishedContentManagerMixin` and `manager`
    """
    return type(
        prefix + manager.__name__,
        (mixin, manager),
        {"use_in_migrations": False},
    )


def replace_manager(model, manager, mixin, **kwargs):
    if hasattr(model, manager) and isinstance(getattr(model, manager), mixin):
        return
    original_manager = getattr(model, manager).__class__ if hasattr(model, manager) else models.Manager
    manager_object = manager_factory(original_manager, "Versioned", mixin)()
    for key, value in kwargs.items():
        setattr(manager_object, key, value)
    model._meta.local_managers = [
        mngr for mngr in model._meta.local_managers if mngr.name != manager
    ]
    model.add_to_class(manager, manager_object)
    if manager == "objects":
        # only safe the original default manager
        model.add_to_class(f'_original_{"manager" if manager == "objects" else manager}', original_manager())


def inject_generic_relation_to_version(model):
    from .models import Version

    model.add_to_class("versions", GenericRelation(Version))


def _set_default_manager(model, manager):
    model._meta.local_managers = [
        m for m in model._meta.local_managers if m.name != "objects"
    ]
    manager_ = copy.copy(manager)
    manager_.name = "objects"
    model.add_to_class("objects", manager_)


@contextmanager
def override_default_manager(model, manager):
    original_manager = model.objects
    _set_default_manager(model, manager)
    yield
    _set_default_manager(model, original_manager)


@contextmanager
def nonversioned_manager(model):
    manager_cls = model.objects.__class__
    manager_cls.versioning_enabled = False
    yield
    manager_cls.versioning_enabled = True


def _version_list_url(versionable, **params):
    proxy = versionable.version_model_proxy
    return add_url_parameters(
        admin_reverse(
            "{app}_{model}_changelist".format(
                app=proxy._meta.app_label, model=proxy._meta.model_name
            )
        ),
        **params
    )


def version_list_url(content):
    """Returns a URL to list of content model versions,
    filtered by `content`'s grouper
    """
    versionable = _cms_extension().versionables_by_content[content.__class__]
    return _version_list_url(
        versionable, **versionable.grouping_values(content, relation_suffix=False)
    )


def version_list_url_for_grouper(grouper):
    """Returns a URL to list of content model versions,
    filtered by `grouper`
    """
    versionable = _cms_extension().versionables_by_grouper[grouper.__class__]
    return _version_list_url(
        versionable, **{versionable.grouper_field_name: str(grouper.pk)}
    )


def is_content_editable(placeholder, user):
    """A helper method for monkey patch to check version is in edit state.
    Returns True if placeholder is related to a source object
    which is not versioned.

    :param placeholder: current placeholder
    :param user: user object
    :return: Boolean
    """
    try:
        versionables.for_content(placeholder.source)
    except KeyError:
        return True
    from .models import Version

    version = Version.objects.get_for_content(placeholder.source)
    return version.state == DRAFT


def get_editable_url(content_obj):
    """If the object is editable the cms editable view should be used, with the toolbar.
       This method is provides the URL for it.
    """
    if is_editable_model(content_obj.__class__):
        language = getattr(content_obj, "language", None)
        url = get_object_edit_url(content_obj, language)
    # Or else, the standard edit view should be used
    else:
        url = reverse(
            "admin:{app}_{model}_change".format(
                app=content_obj._meta.app_label, model=content_obj._meta.model_name
            ),
            args=(content_obj.pk,),
        )
    return url


# TODO Based on polymorphic.query_translate._get_mro_content_type_ids,
# can use that when polymorphic gets a new release
def get_content_types_with_subclasses(models, using=None):
    content_types = set()
    for model in models:
        content_type = ContentType.objects.db_manager(using).get_for_model(
            model, for_concrete_model=False
        )
        content_types.add(content_type.pk)
        subclasses = model.__subclasses__()
        if subclasses:
            content_types.update(get_content_types_with_subclasses(subclasses, using))
    return content_types


def get_preview_url(content_obj):
    """If the object is editable the cms preview view should be used, with the toolbar.
       This method provides the URL for it.
    """
    versionable = versionables.for_content(content_obj)
    if versionable.preview_url:
        return versionable.preview_url(content_obj)

    if is_editable_model(content_obj.__class__):
        url = get_object_preview_url(content_obj)
        # Or else, the standard change view should be used
    else:
        url = reverse(
            "admin:{app}_{model}_change".format(
                app=content_obj._meta.app_label, model=content_obj._meta.model_name
            ),
            args=[content_obj.pk],
        )
    return url


def get_admin_url(model, action, *args):
    opts = model._meta
    url_name = "{}_{}_{}".format(opts.app_label, opts.model_name, action)
    return admin_reverse(url_name, args=args)


def remove_published_where(queryset):
    """
    By default the versioned queryset filters out so that only versions
    that are published are returned. If you need to return the full queryset
    this method can be used.

    It will modify the sql to remove `where state = 'published'`
    """
    where_children = queryset.query.where.children
    all_except_published = [
        lookup for lookup in where_children
        if not (
            lookup.lookup_name == 'exact' and
            lookup.rhs == PUBLISHED and
            lookup.lhs.field.name == 'state'
        )
    ]

    queryset.query.where = WhereNode()
    queryset.query.where.children = all_except_published
    return queryset


def get_latest_admin_viewable_content(grouper, include_unpublished_archived=False, **extra_grouping_fields):
    """
    Return the latest Draft or Published PageContent using the draft where possible
    """
    versionable = versionables.for_grouper(grouper)
    for field in versionable.extra_grouping_fields:
        if field not in extra_grouping_fields:
            raise ValueError(f"Grouping field {field} required for {versionable.grouper_model}.")
    if isinstance(grouper, models.Model):
        # We have an instance? Find reverse relation and utilize the prefetch cache
        content_set = versionable.grouper_field.remote_field.get_accessor_name()
        qs = getattr(grouper, content_set)(manager="admin_manager")
    else:
        qs = versionable.content_model.admin_manager
    if include_unpublished_archived:
        return qs.filter(**extra_grouping_fields).latest_content().first()
    return qs.filter(**extra_grouping_fields).current_content().first()


def get_latest_admin_viewable_page_content(page, language):
    warnings.warn("get_latst_admin_viewable_page_content has ben deprecated. "
                  "Use get_latest_admin_viewable_content(page, language=language) instead.",
                  DeprecationWarning, stacklevel=2)
    return get_latest_admin_viewable_content(page, language=language)


def proxy_model(obj, content_model):
    """
    Get the proxy model from a

    :param obj: A registered versionable object
    :param content_model: A registered content model
    """
    versionable = versionables.for_content(content_model)
    obj_ = copy.deepcopy(obj)
    obj_.__class__ = versionable.version_model_proxy
    return obj_
