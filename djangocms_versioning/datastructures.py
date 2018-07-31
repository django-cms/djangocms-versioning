from django.db.models import Max


class VersionableItem:

    def __init__(self, content_model, grouper_field_name):
        self.content_model = content_model
        self.grouper_field_name = grouper_field_name
        self.grouper_field = self._get_grouper_field()

    def _get_grouper_field(self):
        return self.content_model._meta.get_field(self.grouper_field_name)

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
