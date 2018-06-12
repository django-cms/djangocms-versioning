from django.db import connections, models
from django.db.models import Max, Q
from django.utils.timezone import localtime


class Campaign(models.Model):
    name = models.TextField()
    start = models.DateTimeField(null=True, blank=True)
    end = models.DateTimeField(null=True, blank=True)


class BaseVersionQuerySet(models.QuerySet):

    # extra_filters = Q(content__language='en')
    def for_grouper(self, grouper, extra_filters=None):
        if extra_filters is None:
            extra_filters = Q()
        return self.filter(
            Q(extra_filters) &
            Q((self.model.grouper_field, grouper)),
        )

    def _public_qs(self, when=None):
        if when is None:
            when = localtime()
        return self.filter(
            (
                Q(start__lte=when) |
                Q(campaign__start__lte=when)
            ) & (
                Q(end__gte=when) |
                Q(end__isnull=True) |
                (
                    Q(campaign__isnull=False) &
                    (
                        Q(campaign__end__gte=when) |
                        Q(campaign__end__isnull=True)
                    )
                )
            ) & Q(is_active=True)
        ).order_by('-created')

    def public(self, when=None):
        if when is None:
            when = localtime()
        return self._public_qs(when).first()

    def distinct_groupers(self):
        if connections[self.db].features.can_distinct_on_fields:
            # ?
            return self.distinct(self.model.grouper_field).order_by('-created')
        else:
            inner = self.values(
                self.model.grouper_field,
            ).annotate(Max('pk')).values('pk__max')
            return self.filter(pk__in=inner)


class BaseVersion(models.Model):
    COPIED_FIELDS = ['label', 'campaign', 'start', 'end', 'is_active']

    label = models.TextField()
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    created = models.DateTimeField(auto_now_add=True)
    start = models.DateTimeField(null=True, blank=True)
    end = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    objects = BaseVersionQuerySet.as_manager()

    class Meta:
        abstract = True

    def _copy_func_factory(self, name):
        def inner(new):
            related = getattr(self, name)
            related.pk = None
            related.save()
            return related
        return inner

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

    def copy(self):
        new = self._meta.model(**{
            f: getattr(self, f)
            for f in self.COPIED_FIELDS
        })
        m2m_cache = {}
        relation_fields = self._get_relation_fields()
        for f in relation_fields:
            try:
                copy_func = getattr(self, 'copy_{}'.format(f.name))
            except AttributeError:
                copy_func = self._copy_func_factory(f.name)
            new_value = copy_func(new)
            if f.many_to_many:
                m2m_cache[f.name] = new_value
            else:
                setattr(new, f.name, new_value)
        new.save()
        for field, value in m2m_cache.items():
            getattr(new, field).set(value)
        return new
