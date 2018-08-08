from django.db.models import Max
from django.utils.functional import cached_property

from .models import Version


class VersionableItem:

    def __init__(self, content_model, grouper_field_name, copy_functions=None):
        self.content_model = content_model
        self.grouper_field_name = grouper_field_name
        self.grouper_field = self._get_grouper_field()
        if copy_functions is None:
            self.copy_functions = {}
        else:
            self.copy_functions = copy_functions

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
                'Meta': type('Meta', (), {'proxy': True}),
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
        inner = self.content_model.objects.values(
            self.grouper_field.name,
        ).annotate(Max('pk')).values('pk__max')
        return self.content_model.objects.filter(id__in=inner)

    def for_grouper(self, grouper):
        """Returns all `Content` objects for specified grouper object."""
        return self.content_model.objects.filter(**{self.grouper_field.name: grouper})
