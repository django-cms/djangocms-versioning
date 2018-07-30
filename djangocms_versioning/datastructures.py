from django.db.models import Max, Q


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

    def for_grouper(self, grouper, extra_filters=None):
        """Returns all `Content` objects for specified grouper object.

        Additional filters on content model can be passed via extra_filters,
        for example if versioned content object is translatable, passing
        `Q(language='en')` will return only content objects created for
        English language.
        """

        if extra_filters is None:
            extra_filters = Q()
        return self.content_model.objects.filter(
            Q(**{self.grouper_field.name: grouper}) & extra_filters,
        )
