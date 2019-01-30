from itertools import chain

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Case, Max, OuterRef, Prefetch, Subquery, When
from django.utils.functional import cached_property

from .admin import VersioningAdminMixin
from .constants import DRAFT, PUBLISHED
from .helpers import get_content_types_with_subclasses
from .models import Version


class BaseVersionableItem:
    concrete = False

    def __init__(self, content_model, content_admin_mixin=None):
        self.content_model = content_model
        self.content_admin_mixin = content_admin_mixin or VersioningAdminMixin


class VersionableItem(BaseVersionableItem):
    concrete = True

    def __init__(
        self, content_model, grouper_field_name, copy_function,
        extra_grouping_fields=None, version_list_filter_lookups=None,
        on_publish=None, on_unpublish=None, on_draft_create=None,
        on_archive=None, grouper_selector_option_label=False,
        content_admin_mixin=None, preview_url=None,
    ):
        super().__init__(content_model, content_admin_mixin)
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

    def _get_grouper_field(self):
        return self.content_model._meta.get_field(self.grouper_field_name)

    @cached_property
    def version_model_proxy(self):
        """Returns a dynamically created proxy model class to Version.
        It's used for creating separate version model classes for each
        content type.
        """
        model_name = self.content_model.__name__ + 'Version'

        ProxyVersion = type(
            model_name,
            (Version, ),
            {
                'Meta': type('Meta', (), {'proxy': True, 'managed': False}),
                '__module__': __name__,
                '_source_model': self.content_model,
            },
        )
        return ProxyVersion

    @property
    def grouper_model(self):
        return self.grouper_field.remote_field.model

    def distinct_groupers(self):
        """Returns a queryset of `self.content` objects with unique
        grouper objects.

        Useful for listing, e.g. all Polls.
        """
        inner = self.content_model._base_manager.values(
            self.grouper_field.name,
        ).annotate(Max('pk')).values('pk__max')
        return self.content_model._base_manager.filter(id__in=inner)

    def for_grouper(self, grouper):
        """Returns all `Content` objects for specified grouper object."""
        return self.for_grouping_values(**{self.grouper_field.name: grouper})

    def for_content_grouping_values(self, content):
        """Returns all `Content` objects based on all grouping values
        in specified content object."""
        return self.for_grouping_values(**self.grouping_values(content))

    def for_grouping_values(self, **kwargs):
        """Returns all `Content` objects based on all specified
        grouping values."""
        return self.content_model._base_manager.filter(**kwargs)

    @property
    def grouping_fields(self):
        return chain([self.grouper_field_name], self.extra_grouping_fields)

    def grouping_values(self, content, relation_suffix=True):
        def suffix(field, allow=True):
            if allow and content._meta.get_field(field).is_relation:
                return field + '_id'
            return field
        return {
            suffix(field, allow=relation_suffix): getattr(content, suffix(field))
            for field in self.grouping_fields
        }

    def grouper_choices_queryset(self):
        inner = self.content_model._base_manager.annotate(
            order=Case(
                When(versions__state=PUBLISHED, then=2),
                When(versions__state=DRAFT, then=1),
                default=0,
                output_field=models.IntegerField(),
            ),
        ).filter(**{
            self.grouper_field_name: OuterRef('pk'),
        }).order_by('-order')
        content_objects = self.content_model._base_manager.filter(
            pk__in=self.grouper_model._base_manager.annotate(
                content=Subquery(inner.values_list('pk')[:1]),
            ).values_list('content'),
        )
        cache_name = self.grouper_field.remote_field.get_accessor_name()
        return self.grouper_model._base_manager.prefetch_related(
            Prefetch(cache_name, queryset=content_objects),
        )

    def get_grouper_with_fallbacks(self, grouper_id):
        return self.grouper_choices_queryset().filter(pk=grouper_id).first()

    def _get_content_types(self):
        return [ContentType.objects.get_for_model(self.content_model).pk]

    @cached_property
    def content_types(self):
        return self._get_content_types()

    def get_preview_url(self, content):
        if self.preview_url is None:
            return
        return self.preview_url(content)


class PolymorphicVersionableItem(VersionableItem):
    """VersionableItem for use by base polymorphic class
    (for example filer.File).
    """

    def _get_content_types(self):
        return get_content_types_with_subclasses([self.content_model])


class VersionableItemAlias(BaseVersionableItem):
    """VersionableItem that points to a different VersionableItem,
    so that all operations are executed in context of
    the other VersionableItem.
    """

    def __init__(self, content_model, to, content_admin_mixin=None):
        super().__init__(content_model, content_admin_mixin)
        self.to = to

    def __getattr__(self, name):
        return getattr(self.to, name)


def default_copy(original_content):
    """Copy all fields of the original content object exactly as they are
    and return a new content object which is different only in its pk.

    NOTE: This will only work for very simple content objects. This will
    throw exceptions on one2one and m2m relationships. And it might not
    be the desired behaviour for some foreign keys (in some cases we
    would expect a version to copy some of its related objects as well).
    In such cases a custom copy method must be defined and specified in
    cms_config.py
    """
    content_model = original_content.__class__
    content_fields = {
        field.name: getattr(original_content, field.name)
        for field in content_model._meta.fields
        # don't copy primary key because we're creating a new obj
        if content_model._meta.pk.name != field.name
    }
    return content_model.objects.create(**content_fields)
