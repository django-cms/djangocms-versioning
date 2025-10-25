from __future__ import annotations

from collections.abc import Iterable
from itertools import chain
from typing import Any

from cms.extensions.models import BaseExtension
from cms.models import Placeholder, PlaceholderRelationField
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.functional import cached_property

from .admin import DefaultGrouperVersioningAdminMixin, VersioningAdminMixin
from .helpers import get_content_types_with_subclasses
from .models import Version


class BaseVersionableItem:
    concrete = False

    def __init__(self, content_model: type[models.Model], content_admin_mixin: type | None = None):
        self.content_model = content_model
        self.content_admin_mixin = content_admin_mixin or VersioningAdminMixin


class VersionableItem(BaseVersionableItem):
    concrete = True

    def __init__(
        self,
        content_model: type[models.Model],
        grouper_field_name: str,
        copy_function: callable,
        extra_grouping_fields: Iterable[str] | None = None,
        version_list_filter_lookups: dict[str, Any] | None = None,
        on_publish=None,
        on_unpublish=None,
        on_draft_create=None,
        on_archive=None,
        grouper_selector_option_label=False,
        grouper_admin_mixin: type | None = None,
        content_admin_mixin: type | None = None,
        preview_url=None,
    ):
        super().__init__(content_model, content_admin_mixin)
        # Process the grouper admin mixin:
        # For backward compatibility, we need to mark the new default (instead of just applying it)
        self.grouper_admin_mixin = (
            DefaultGrouperVersioningAdminMixin if grouper_admin_mixin == "__default__" else grouper_admin_mixin
        )
        # Set the grouper field
        self.grouper_field_name = grouper_field_name
        self.grouper_field = self._get_grouper_field()
        self.extra_grouping_fields = extra_grouping_fields or ()
        # Set the grouper selector label
        self.grouper_selector_option_label = grouper_selector_option_label
        self.version_list_filter_lookups = version_list_filter_lookups or {}
        self.copy_function = copy_function
        self.on_publish = on_publish
        self.on_unpublish = on_unpublish
        self.on_draft_create = on_draft_create
        self.on_archive = on_archive
        self.preview_url = preview_url

    def _get_grouper_field(self) -> models.Field:
        """Get the grouper field on the content model

        :return: instance of a django model field
        """
        return self.content_model._meta.get_field(self.grouper_field_name)

    @cached_property
    def version_model_proxy(self) -> type[Version]:
        """Returns a dynamically created proxy model class to Version.
        It's used for creating separate version model classes for each
        content type.
        """
        model_name = self.content_model.__name__ + "Version"

        ProxyVersion = type(
            model_name,
            (Version,),
            {
                "Meta": type("Meta", (), {"proxy": True, "managed": False}),
                "__module__": __name__,
                "_source_model": self.content_model,
            },
        )
        return ProxyVersion

    @property
    def grouper_model(self) -> type[models.Model]:
        """Returns the grouper model class"""
        return self.grouper_field.remote_field.model

    @cached_property
    def content_model_is_sideframe_editable(self) -> bool:
        """Determine if a content model can be opened in the sideframe or not.

        :return: Default True, False if the content model is not suitable for the sideframe
        :rtype: bool
        """
        from cms.models import Placeholder

        # Any models that contain a placeholder are deemed as not sideframe editing
        # compatible i.e. they are toolbar enabled and contain placeholders. We can't
        # use toolbar enabled status alone because any models that use version compare
        # enable the toolbar to display.
        for field in self.content_model._meta.get_fields(include_hidden=True):
            if field.related_model == Placeholder:
                return False
        return True

    def distinct_groupers(self, **kwargs) -> models.QuerySet:
        """Returns a queryset of `self.content` objects with unique
        grouper objects.

        Useful for listing, e.g. all Polls.

        :param kwargs: Optional filtering parameters for inner queryset
        """
        queryset = self.content_model.admin_manager.values(self.grouper_field.name).filter(**kwargs)
        inner = queryset.annotate(models.Max("pk")).values("pk__max")
        return self.content_model.admin_manager.filter(id__in=inner)

    def for_grouper(self, grouper: models.Model) -> models.QuerySet:
        """Returns all `Content` objects for specified grouper object."""
        return self.for_grouping_values(**{self.grouper_field.name: grouper})

    def for_content_grouping_values(self, content: models.Model) -> models.QuerySet:
        """Returns all `Content` objects based on all grouping values
        in specified content object."""
        return self.for_grouping_values(**self.grouping_values(content))

    def for_grouping_values(self, **kwargs) -> models.QuerySet:
        """Returns all `Content` objects based on all specified
        grouping values."""
        return self.content_model.admin_manager.filter(**kwargs)

    @property
    def grouping_fields(self) -> Iterable[str]:
        """Returns an iterator for all the grouping fields"""
        return chain([self.grouper_field_name], self.extra_grouping_fields)

    def grouping_values(self, content: models.Model, relation_suffix: bool = True) -> dict[str, Any]:
        """Returns a dict of grouper fields as keys and values from the content instance

        :param content: instance of a content model
        :param relation_suffix: bool setting whether fk fieldnames have '_id' added
        :return: a dict like {'grouping_field1': content.grouping_field1, ...}
        """

        def suffix(field, allow=True):
            if allow and content._meta.get_field(field).is_relation:
                return field + "_id"
            return field

        return {suffix(field, allow=relation_suffix): getattr(content, suffix(field)) for field in self.grouping_fields}

    def grouper_choices_queryset(self) -> models.QuerySet:
        """Returns a queryset of all the available groupers instances of the registered type"""
        content_objects = self.content_model.admin_manager.all().latest_content()
        cache_name = self.grouper_field.remote_field.get_accessor_name()
        return self.grouper_model._base_manager.prefetch_related(models.Prefetch(cache_name, queryset=content_objects))

    def get_grouper_with_fallbacks(self, grouper_id) -> models.Model | None:
        return self.grouper_choices_queryset().filter(pk=grouper_id).first()

    def _get_content_types(self) -> set[int]:
        return {ContentType.objects.get_for_model(self.content_model).pk}

    @cached_property
    def content_types(self) -> set[int]:
        """Get the primary key of the content type of the registered content model.

        :return:  A list with the primary keys of the content types
        """
        # NOTE: If using this class this will be a list with one element,
        # but PolymorphicVersionableItem overrides this and can return
        # more elements
        return self._get_content_types()


class PolymorphicVersionableItem(VersionableItem):
    """VersionableItem for use by base polymorphic class (for example filer.File)."""

    def _get_content_types(self) -> set[int]:
        return get_content_types_with_subclasses([self.content_model])


class VersionableItemAlias(BaseVersionableItem):
    """VersionableItem that points to a different VersionableItem,
    so that all operations are executed in context of
    the other VersionableItem.
    """

    def __init__(
        self, content_model: type[models.Model], to: BaseVersionableItem, content_admin_mixin: type | None = None
    ):
        super().__init__(content_model, content_admin_mixin)
        self.to = to

    def __getattr__(self, name: str) -> Any:
        return getattr(self.to, name)


def copy_placeholder(original_placeholder: Placeholder, new_content: models.Model) -> Placeholder:
    placeholder_fields = {
        field.name: getattr(original_placeholder, field.name)
        for field in Placeholder._meta.fields
        if field.name not in [Placeholder._meta.pk.name, "source"]
    }
    if original_placeholder.source:
        placeholder_fields["source"] = new_content
    new_placeholder = Placeholder.objects.create(**placeholder_fields)
    original_placeholder.copy_plugins(new_placeholder)
    return new_placeholder


def default_copy(original_content: models.Model) -> models.Model:
    """Copy all fields of the original content object exactly as they are
    and return a new content object which is different only in its pk.

    NOTE: This will only work for very simple content objects.

    It copies placeholders and their plugins, and any extension (subclass
    of cms.extensions.base.BaseExtension).

    It will throw exceptions on one2one and m2m relationships. And it might not
    be the desired behaviour for some foreign keys (in some cases we
    would expect a version to copy some of its related objects as well).
    In such cases a custom copy method must be defined and specified in
    cms_config.py

    NOTE: A custom copy method will need to use the content model's
    _original_manager to create only a content model object and not
    also a Version object.
    """
    content_model = original_content.__class__
    content_fields = {
        field.name: getattr(original_content, field.name)
        for field in content_model._meta.fields
        # don't copy primary key because we're creating a new obj
        if content_model._meta.pk.name != field.name
    }
    # Use original manager to not create a new Version object here
    new_content = content_model._original_manager.create(**content_fields)

    # Now copy PlaceholderRelationFields
    for field in content_model._meta.private_fields:
        # Copy PlaceholderRelationFields
        if isinstance(field, PlaceholderRelationField):
            # Copy placeholders
            original_placeholders = getattr(original_content, field.name).all()
            new_placeholders = [copy_placeholder(ph, new_content) for ph in original_placeholders]
            getattr(new_content, field.name).add(*new_placeholders)
        if hasattr(new_content, "copy_relations"):
            if callable(new_content.copy_relations):
                new_content.copy_relations()

    # If pagecontent has an associated extension, also copy it!
    for field in content_model._meta.related_objects:
        if hasattr(original_content, field.name):
            extension = getattr(original_content, field.name)
            if isinstance(extension, BaseExtension):
                extension.copy(new_content, language=getattr(new_content, "language", None))

    return new_content
