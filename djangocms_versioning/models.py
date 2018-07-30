from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q


class VersionQuerySet(models.QuerySet):

    def for_grouper(self, grouper, extra_filters=None):
        """Returns all `Version`s for specified grouper object.

        Additional filters can be passed via extra_filters, for example
        if version model has a FK to content object that is translatable,
        passing `Q(language='en')` will return only versions
        created for English language.
        """

        if extra_filters is None:
            extra_filters = Q()
        return self.filter(
            Q(extra_filters) &
            Q((self.model.grouper_field, grouper)),
        )


class Version(models.Model):
    # Following fields are always copied from original Version
    COPIED_FIELDS = ['label']

    label = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    content_type = models.ForeignKey(
        ContentType,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    object_id = models.PositiveIntegerField(blank=True, null=True)
    content = GenericForeignKey('content_type', 'object_id')

    objects = VersionQuerySet.as_manager()

    def _copy_function_factory(self, field):
        """
        Factory for a dynamically defined function that considers the relationship type
        (1-2-M or M-2-M), when copying related objects between model instances.
        :param field: Related object.
        :return: Specific kind of object copy function.
        """
        def inner(new):
            related = getattr(self, field.name)
            initial = {
                f.name: getattr(related, f.name)
                for f in related._meta.fields if not f.auto_created
            }
            new_related = related._meta.model(**initial)
            new_related.save()
            return new_related

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
        m2m_cache = {}

        for field in relation_fields:
            try:
                copy_function = getattr(self, 'copy_{}'.format(field.name))
            except AttributeError:
                copy_function = self._copy_function_factory(field)

            new_value = copy_function(new)
            if field.many_to_many:
                if len(new_value):
                    m2m_cache[field.name] = new_value
            else:
                setattr(new, field.name, new_value)

        # Must save object before adding M2M relations.
        new.save()

        for field_name, objects in m2m_cache.items():
            getattr(new, field_name).set(objects)

        return new
