import copy
import typing
import warnings
from contextlib import contextmanager

from cms.models import Page, PageContent, Placeholder
from cms.toolbar.utils import get_object_edit_url, get_object_preview_url
from cms.utils.helpers import is_editable_model
from cms.utils.urlutils import add_url_parameters, admin_reverse
from django.conf import settings
from django.contrib import admin
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.mail import EmailMessage
from django.db import models
from django.template.loader import render_to_string
from django.utils.encoding import force_str
from django.utils.translation import get_language

from . import versionables
from .conf import EMAIL_NOTIFICATIONS_FAIL_SILENTLY
from .constants import DRAFT

try:
    from djangocms_internalsearch.helpers import emit_content_change
except ImportError:
    emit_content_change = None


def is_editable(content_obj, request):
    """Check of content_obj is editable"""
    from .models import Version

    return Version.objects.get_for_content(content_obj).check_modify.as_bool(
        request.user
    )


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
            f"{versionable.version_model_proxy!r} is already registered with admin.",
            UserWarning,
            stacklevel=2,
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
    original_manager = (
        getattr(model, manager).__class__ if hasattr(model, manager) else models.Manager
    )
    manager_object = manager_factory(original_manager, "Versioned", mixin)()
    for key, value in kwargs.items():
        setattr(manager_object, key, value)
    model._meta.local_managers = [
        mngr for mngr in model._meta.local_managers if mngr.name != manager
    ]
    model.add_to_class(manager, manager_object)
    if manager == "objects":
        # only safe the original default manager
        model.add_to_class(
            f'_original_{"manager" if manager == "objects" else manager}',
            original_manager(),
        )


def inject_generic_relation_to_version(model):
    from .models import Version

    related_query_name = f"{model._meta.app_label}_{model._meta.model_name}"
    model.add_to_class(
        "versions", GenericRelation(Version, related_query_name=related_query_name)
    )
    if not hasattr(model, "is_editable"):
        model.add_to_class("is_editable", is_editable)


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
        admin_reverse(f"{proxy._meta.app_label}_{proxy._meta.model_name}_changelist"),
        **params,
    )


def version_list_url(content):
    """Returns a URL to list of content model versions,
    filtered by `content`'s grouper
    """
    versionable = versionables._cms_extension().versionables_by_content[
        content.__class__
    ]
    return _version_list_url(
        versionable, **versionable.grouping_values(content, relation_suffix=False)
    )


def version_list_url_for_grouper(grouper):
    """Returns a URL to list of content model versions,
    filtered by `grouper`
    """
    versionable = versionables._cms_extension().versionables_by_grouper[
        grouper.__class__
    ]
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


def get_editable_url(content_obj, force_admin=False):
    """If the object is editable the cms editable view should be used, with the toolbar.
    This method provides the URL for it.
    """
    if is_editable_model(content_obj.__class__) and not force_admin:
        language = getattr(content_obj, "language", None)
        url = get_object_edit_url(content_obj, language)
    # Or else, the standard edit view should be used
    else:
        url = admin_reverse(
            f"{content_obj._meta.app_label}_{content_obj._meta.model_name}_change",
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


def get_preview_url(
    content_obj: models.Model, language: typing.Union[str, None] = None
) -> str:
    """If the object is editable the cms preview view should be used, with the toolbar.
    This method provides the URL for it. It falls back the standard change view
    should the object not be frontend editable.
    """
    versionable = versionables.for_content(content_obj)
    if versionable.preview_url:
        return versionable.preview_url(content_obj)
    if is_editable_model(content_obj.__class__):
        if not language:
            # Use language field is content object has one to determine the language
            language = getattr(content_obj, "language", get_language())
        url = get_object_preview_url(content_obj, language=language)
    else:
        # Or else, the standard change view should be used
        url = admin_reverse(
            f"{content_obj._meta.app_label}_{content_obj._meta.model_name}_change",
            args=[content_obj.pk],
        )
        if language:
            url += f"&language={language}"
    return url


def get_admin_url(model: type, action: str, *args) -> str:
    opts = model._meta
    url_name = f"{opts.app_label}_{opts.model_name}_{action}"
    return admin_reverse(url_name, args=args)


def remove_published_where(queryset):
    """
    By default, the versioned queryset filters out so that only versions
    that are published are returned. If you need to return the full queryset
    use the "admin_manager" instead of "objects"
    """
    raise NotImplementedError(
        "remove_published_where has been replaced by ContentObj.admin_manager"
    )


def get_latest_admin_viewable_content(
    grouper: models.Model,
    include_unpublished_archived: bool = False,
    **extra_grouping_fields,
) -> models.Model:
    """
    Return the latest Draft or Published PageContent using the draft where possible
    """
    versionable = versionables.for_grouper(grouper)

    # Check if all required grouping fields are given to be able to select the latest admin viewable content
    missing_fields = [
        field
        for field in versionable.extra_grouping_fields
        if field not in extra_grouping_fields
    ]
    if missing_fields:
        raise ValueError(
            f"Grouping field(s) {missing_fields} required for {versionable.grouper_model}."
        )

    # Get the name of the content_set (e.g., "pagecontent_set") from the versionable
    content_set = versionable.grouper_field.remote_field.get_accessor_name()

    # Accessing the content set through the grouper preserves prefetches
    qs = getattr(grouper, content_set)(manager="admin_manager")

    if include_unpublished_archived:
        # Relevant for admin to see e.g., the latest unpublished or archived versions
        return qs.filter(**extra_grouping_fields).latest_content().first()
    # Return only active versions, e.g., for copying
    return qs.filter(**extra_grouping_fields).current_content().first()


def get_latest_admin_viewable_page_content(
    page: Page, language: str
) -> PageContent:  # pragma: no cover
    warnings.warn(
        "get_latst_admin_viewable_page_content has ben deprecated. "
        "Use get_latest_admin_viewable_content(page, language=language) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_latest_admin_viewable_content(page, language=language)


def proxy_model(obj: models.Model, content_model: type) -> models.Model:
    """
    Get the proxy model from a

    :param obj: A registered versionable object
    :param content_model: A registered content model
    """
    versionable = versionables.for_content(content_model)
    obj_ = copy.deepcopy(obj)
    obj_.__class__ = versionable.version_model_proxy
    return obj_


def create_version_lock(version, user):
    """
    Create a version lock if necessary
    """
    changed = version.locked_by != user
    version.locked_by = user
    version.save()
    if changed and emit_content_change:
        emit_content_change(version.content)
    return version


def remove_version_lock(version):
    """
    Delete a version lock, handles when there are none available.
    """
    return create_version_lock(version, None)


def version_is_locked(version) -> settings.AUTH_USER_MODEL:
    """
    Determine if a version is locked
    """
    return version.locked_by


def version_is_unlocked_for_user(version, user: settings.AUTH_USER_MODEL) -> bool:
    """Check if lock doesn't exist for a version object or is locked to provided user."""
    return version.locked_by is None or version.locked_by == user


def content_is_unlocked_for_user(
    content: models.Model, user: settings.AUTH_USER_MODEL
) -> bool:
    """Check if lock doesn't exist or object is locked to provided user."""
    try:
        if hasattr(content, "prefetched_versions"):
            version = content.prefetched_versions[0]
        else:
            version = content.versions.first()
        return version_is_unlocked_for_user(version, user)
    except AttributeError:
        return True


def placeholder_content_is_unlocked_for_user(
    placeholder: Placeholder, user: settings.AUTH_USER_MODEL
) -> bool:
    """Check if lock doesn't exist or placeholder source object
    is locked to provided user.
    """
    content = placeholder.source
    return content_is_unlocked_for_user(content, user)


def send_email(
    recipients: list, subject: str, template: str, template_context: dict
) -> int:
    """
    Send emails using locking templates
    """
    template = f"djangocms_versioning/emails/{template}"
    subject = force_str(subject)
    content = render_to_string(template, template_context)

    message = EmailMessage(
        subject=subject,
        body=content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )
    return message.send(fail_silently=EMAIL_NOTIFICATIONS_FAIL_SILENTLY)


def get_latest_draft_version(version: models.Model) -> models.Model:
    """Get latest draft version of version object and caches it in the
    content object"""
    from .models import Version

    if (
        not hasattr(version.content, "_latest_draft_version")
        or getattr(version.content._latest_draft_version, "state", DRAFT) != DRAFT
    ):
        drafts = Version.objects.filter_by_content_grouping_values(
            version.content
        ).filter(state=DRAFT)
        version.content._latest_draft_version = drafts.first()
    return version.content._latest_draft_version
