from django.core.exceptions import ImproperlyConfigured
from django.db import connections, models
from django.db.models import Max, Q
from django.utils.timezone import localtime


class Campaign(models.Model):
    name = models.TextField()
    start = models.DateTimeField(null=True, blank=True)
    end = models.DateTimeField(null=True, blank=True)


class BaseVersionQuerySet(models.QuerySet):

    def for_grouper(self, grouper, extra_filters=None):
        """Returns all `Version`s for specified grouper object.

        Additional filters can be passed via extra_filters, for example
        if version model has a FK to content object that is translatable,
        passing `Q(content__language='en')` will return only versions
        created for English language.
        """
        if extra_filters is None:
            extra_filters = Q()
        return self.filter(
            Q(extra_filters) &
            Q((self.model.grouper_field, grouper)),
        )

    def _public_qs(self, when):
        return self.filter(
            (
                Q(start__lte=when) |
                Q(campaigns__start__lte=when)
            ) & (
                Q(end__gte=when) |
                Q(end__isnull=True) |
                (
                    Q(campaigns__isnull=False) &
                    (
                        Q(campaigns__end__gte=when) |
                        Q(campaigns__end__isnull=True)
                    )
                )
            ) & Q(is_active=True)
        ).order_by('-created')

    def public(self, when=None):
        """Returns `Version` considered as public for a given date
        in `when` (or present time when `when` is omitted).

        Rules used to determine returned version:
        - start field must be filled and start < `when`
        - end field is empty
          (meaning that publication of that version never ends)
            OR
          end field > `when`
        - is_active is True (Version hasn't been disabled)
        - most recent (in terms of creation) version of the ones meeting
          above criteria is chosen

        Returned version:

             V1   V2   V3        None   V4
             |    |    |          |     |
             v    v    v          v     v
        V4                            -----
        V3            -----
        V2       ----------------
        V1  -----------------

        ---- - Publication time frame
               (from `Version` object and related `Campaign` combined)
        """
        if when is None:
            when = localtime()
        return self._public_qs(when).first()

    def distinct_groupers(self):
        """Returns a queryset of `Version` objects with unique
        grouper objects.

        Useful for listing, e.g. all Polls.
        """
        if connections[self.db].features.can_distinct_on_fields:
            return self.distinct(self.model.grouper_field).order_by('-created')
        else:
            inner = self.values(self.model.grouper_field).annotate(
                Max('pk')).values('pk__max')
            return self.filter(pk__in=inner)


class BaseVersion(models.Model):
    # Following fields are always copied from original Version
    COPIED_FIELDS = ['label', 'start', 'end', 'is_active']

    label = models.TextField()
    campaigns = models.ManyToManyField(
        Campaign,
        blank=True,
    )
    created = models.DateTimeField(auto_now_add=True)
    start = models.DateTimeField(null=True, blank=True)
    end = models.DateTimeField(null=True, blank=True)

    # Used to disable versions
    is_active = models.BooleanField(default=True)

    objects = BaseVersionQuerySet.as_manager()

    class Meta:
        abstract = True

    def _copy_function_factory(self, field):
        """
        Factory for a dynamically defined function that considers the relationship type
        (1-2-M or M-2-M), when copying related objects between model instances.
        :param field: Related object.
        :return: Specific kind of object copy function.
        """
        def inner(new):
            related = getattr(self, field.name)
            related.pk = None
            related.save()
            return related

        def inner_m2m(new):
            related = getattr(self, field.name)
            related_objects = related.all()
            return related_objects

        inner_copy = inner_m2m if field.many_to_many else inner
        return inner_copy

    def _get_relation_fields(self):
        """Returns a list of relation fields to copy over.
        If copy_field_order is present, sorts the outcome
        based on the list of field names
        """
        relation_fields = [
            f for f in self._meta.get_fields() if
            f.is_relation and
            f.name not in self.COPIED_FIELDS and
            not f.auto_created
        ]
        if getattr(self, 'copy_field_order', None):
            relation_fields = sorted(
                relation_fields,
                key=lambda f: self.copy_field_order.index(f.name),
            )
        return relation_fields

    @property
    def grouper_field(self):
        """Stub for runtime error handling - override.
        """
        raise ImproperlyConfigured(
            'Versioning - You must define grouper_field on the {} model.'.format(
                self.__class__.__name__))

    def copy(self):
        """Creates new Version object, with metadata copied over
        from self.

        Introspects relations and duplicates objects that
        Version has a relation to. Default behaviour for duplication is
        implemented in `_copy_function_factory`. This can be overriden
        per-field by implementing `copy_{field_name}` method.
        """
        new = self._meta.model(**{
            f: getattr(self, f)
            for f in self.COPIED_FIELDS
        })

        relation_fields = self._get_relation_fields()

        for field in relation_fields:
            try:
                copy_function = getattr(self, 'copy_{}'.format(field.name))
            except AttributeError:
                copy_function = self._copy_function_factory(field)

            new_value = copy_function(new)
            m2m_cache = {}
            if field.many_to_many:
                if len(new_value):
                    m2m_cache[field.name] = new_value
            else:
                setattr(new, field.name, new_value)

        # Must save object before adding M2M relations.
        new.save()

        for field_name, objects in m2m_cache.items():
            getattr(new, field_name).add(*objects)

        return new
