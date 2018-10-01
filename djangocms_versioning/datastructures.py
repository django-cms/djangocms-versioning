from itertools import chain

from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models import Case, Max, OuterRef, Prefetch, Subquery, When
from django.utils.functional import cached_property

from .constants import DRAFT, PUBLISHED
from .models import Version


class VersionableItem:

    def __init__(
        self, content_model, grouper_field_name, copy_function,
        extra_grouping_fields=None, version_list_filter_lookups=None,
        on_publish=None, on_unpublish=None, on_draft_create=None,
        on_archive=None, grouper_selector_option_label=False,
    ):
        # We require get_absolute_url to be implemented on content models
        # because it is needed for django-cms's preview endpoint, which
        # we use to generate version comparisons
        if not hasattr(content_model, 'get_absolute_url'):
            error_msg = "{} needs to implement get_absolute_url".format(
                    content_model.__name__)
            raise ImproperlyConfigured(error_msg)
        self.content_model = content_model
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
        return self.for_grouping_values(**self.grouping_values(content))

    def for_grouping_values(self, **kwargs):
        return self.content_model._base_manager.filter(**kwargs)

    @property
    def grouping_fields(self):
        return chain([self.grouper_field_name], self.extra_grouping_fields)

    def grouping_values(self, content):
        fields = (
            field + '_id' if content._meta.get_field(field).is_relation else field
            for field in self.grouping_fields
        )
        return {
            field: getattr(content, field) for field in fields
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
            pk__in=self.grouper_model.objects.annotate(
                content=Subquery(inner.values_list('pk')[:1]),
            ).values_list('content'),
        )
        cache_name = self.grouper_field.remote_field.get_accessor_name()
        return self.grouper_model.objects.prefetch_related(
            Prefetch(cache_name, queryset=content_objects),
        )

    def get_grouper_with_fallbacks(self, grouper_id):
        return self.grouper_choices_queryset().filter(pk=grouper_id).first()


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
