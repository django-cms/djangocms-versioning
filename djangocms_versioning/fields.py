from django.contrib.contenttypes.fields import GenericRel, GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db import DEFAULT_DB_ALIAS
from django.db.models.query_utils import PathInfo
from django.db.models.fields.related import ForeignObject, lazy_related_operation
from django.db.models.fields.related_descriptors import ReverseOneToOneDescriptor

from .compat import DJANGO_GTE_20


class ReverseGenericOneToOneDescriptor(ReverseOneToOneDescriptor):

    def get_queryset(self, **hints):
        related_model = self.related.related_model

        if getattr(related_model._default_manager, 'use_for_related_fields', False):
            if not getattr(related_model._default_manager, 'silence_use_for_related_fields_deprecation', False):
                warnings.warn(
                    "use_for_related_fields is deprecated, instead "
                    "set Meta.base_manager_name on '{}'.".format(related_model._meta.label),
                    RemovedInDjango20Warning, 2
                )
            manager = related_model._default_manager
        else:
            manager = related_model._base_manager

        return manager.db_manager(hints=hints).all()

    def get_prefetch_queryset(self, instances, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        queryset._add_hints(instance=instances[0])

        rel_obj_attr = attrgetter(self.related.field.attname)

        def instance_attr(obj):
            return obj._get_pk_val()

        instances_dict = {instance_attr(inst): inst for inst in instances}
        query = {'%s__in' % self.related.field.name: instances}
        queryset = queryset.filter(**query)

        # Since we're going to assign directly in the cache,
        # we must manage the reverse relation cache manually.
        rel_obj_cache_name = self.related.field.get_cache_name()
        for rel_obj in queryset:
            instance = instances_dict[rel_obj_attr(rel_obj)]
            setattr(rel_obj, rel_obj_cache_name, instance)
        return queryset, rel_obj_attr, instance_attr, True, self.cache_name

    def __get__(self, instance, cls=None):
        if instance is None:
            return self

        try:
            rel_obj = getattr(instance, self.cache_name)
        except AttributeError:
            related_pk = instance._get_pk_val()
            if related_pk is None:
                rel_obj = None
            else:
                filter_args = self.related.field.get_forward_related_filter(instance)
                try:
                    rel_obj = self.get_queryset(instance=instance).get(**filter_args)
                except self.related.related_model.DoesNotExist:
                    rel_obj = None
                else:
                    # Set the forward accessor cache on the related object to
                    # the current instance to avoid an extra SQL query if it's
                    # accessed later on.
                    setattr(rel_obj, self.related.field.get_cache_name(), instance)
            setattr(instance, self.cache_name, rel_obj)

        if rel_obj is None:
            raise self.RelatedObjectDoesNotExist(
                "%s has no %s." % (
                    instance.__class__.__name__,
                    self.related.get_accessor_name()
                )
            )
        else:
            return rel_obj

    def __set__(self, instance, value):
        """
        Set the related instance through the reverse relation.

        With the example above, when setting ``place.restaurant = restaurant``:

        - ``self`` is the descriptor managing the ``restaurant`` attribute
        - ``instance`` is the ``place`` instance
        - ``value`` is the ``restaurant`` instance on the right of the equal sign

        Keep in mind that ``Restaurant`` holds the foreign key to ``Place``.
        """
        # The similarity of the code below to the code in
        # ForwardManyToOneDescriptor is annoying, but there's a bunch
        # of small differences that would make a common base class convoluted.

        if value is None:
            # Update the cached related instance (if any) & clear the cache.
            try:
                rel_obj = getattr(instance, self.cache_name)
            except AttributeError:
                pass
            else:
                delattr(instance, self.cache_name)
                setattr(rel_obj, self.related.field.name, None)
        elif not isinstance(value, self.related.related_model):
            # An object must be an instance of the related class.
            raise ValueError(
                'Cannot assign "%r": "%s.%s" must be a "%s" instance.' % (
                    value,
                    instance._meta.object_name,
                    self.related.get_accessor_name(),
                    self.related.related_model._meta.object_name,
                )
            )
        else:
            if instance._state.db is None:
                instance._state.db = router.db_for_write(instance.__class__, instance=value)
            elif value._state.db is None:
                value._state.db = router.db_for_write(value.__class__, instance=instance)
            elif value._state.db is not None and instance._state.db is not None:
                if not router.allow_relation(value, instance):
                    raise ValueError('Cannot assign "%r": the current database router prevents this relation.' % value)

            related_pk = tuple(getattr(instance, field.attname) for field in self.related.field.foreign_related_fields)
            # Set the value of the related field to the value of the related object's related field
            for index, field in enumerate(self.related.field.local_related_fields):
                setattr(value, field.attname, related_pk[index])

            # Set the related instance cache used by __get__ to avoid an SQL query
            # when accessing the attribute we just set.
            setattr(instance, self.cache_name, value)

            # Set the forward accessor cache on the related object to the current
            # instance to avoid an extra SQL query if it's accessed later on.
            setattr(value, self.related.field.get_cache_name(), instance)


class GenericOneToOneField(ForeignObject):
    """
    """
    auto_created = False

    many_to_many = False
    many_to_one = False
    one_to_many = False
    one_to_one = True

    rel_class = GenericRel
    # forward_related_accessor_class = ReverseGenericOneToOneDescriptor

    def __init__(self, to, object_id_field='object_id', content_type_field='content_type',
                 for_concrete_model=True, related_query_name=None, limit_choices_to=None, **kwargs):
        kwargs['rel'] = self.rel_class(
            self, to,
            related_query_name=related_query_name,
            limit_choices_to=limit_choices_to,
        )

        kwargs['blank'] = True
        kwargs['on_delete'] = models.CASCADE
        kwargs['editable'] = False
        kwargs['serialize'] = False

        # This construct is somewhat of an abuse of ForeignObject. This field
        # represents a relation from pk to object_id field. But, this relation
        # isn't direct, the join is generated reverse along foreign key. So,
        # the from_field is object_id field, to_field is pk because of the
        # reverse join.
        super().__init__(
            to, from_fields=[object_id_field], to_fields=[], **kwargs)

        self.object_id_field_name = object_id_field
        self.content_type_field_name = content_type_field
        self.for_concrete_model = for_concrete_model

    def check(self, **kwargs):
        errors = super(GenericRelation, self).check(**kwargs)
        errors.extend(self._check_generic_foreign_key_existence())
        return errors

    def _is_matching_generic_foreign_key(self, field):
        """
        Return True if field is a GenericForeignKey whose content type and
        object id fields correspond to the equivalent attributes on this
        GenericRelation.
        """
        return (
            isinstance(field, GenericForeignKey) and
            field.ct_field == self.content_type_field_name and
            field.fk_field == self.object_id_field_name
        )

    def _check_generic_foreign_key_existence(self):
        target = self.remote_field.model
        if isinstance(target, ModelBase):
            fields = target._meta.private_fields
            if any(self._is_matching_generic_foreign_key(field) for field in fields):
                return []
            else:
                return [
                    checks.Error(
                        "The GenericRelation defines a relation with the model "
                        "'%s.%s', but that model does not have a GenericForeignKey." % (
                            target._meta.app_label, target._meta.object_name
                        ),
                        obj=self,
                        id='contenttypes.E004',
                    )
                ]
        else:
            return []

    def resolve_related_fields(self):
        self.to_fields = [self.model._meta.pk.name]
        return [(self.remote_field.model._meta.get_field(self.object_id_field_name), self.model._meta.pk)]

    def _get_path_info_with_parent(self):
        """
        Return the path that joins the current model through any parent models.
        The idea is that if you have a GFK defined on a parent model then we
        need to join the parent model first, then the child model.
        """
        # With an inheritance chain ChildTag -> Tag and Tag defines the
        # GenericForeignKey, and a TaggedItem model has a GenericRelation to
        # ChildTag, then we need to generate a join from TaggedItem to Tag
        # (as Tag.object_id == TaggedItem.pk), and another join from Tag to
        # ChildTag (as that is where the relation is to). Do this by first
        # generating a join to the parent model, then generating joins to the
        # child models.
        path = []
        opts = self.remote_field.model._meta.concrete_model._meta
        parent_opts = opts.get_field(self.object_id_field_name).model._meta
        target = parent_opts.pk
        pathinfo_data = dict(
            from_opts=self.model._meta,
            to_opts=parent_opts,
            target_fields=(target,),
            join_field=self.remote_field,
            m2m=True,
            direct=False,
        )
        if DJANGO_GTE_20:
            pathinfo_data.update(dict(
                filtered_relation=filtered_relation,
            ))
        path.append(PathInfo(**pathinfo_data))
        # Collect joins needed for the parent -> child chain. This is easiest
        # to do if we collect joins for the child -> parent chain and then
        # reverse the direction (call to reverse() and use of
        # field.remote_field.get_path_info()).
        parent_field_chain = []
        while parent_opts != opts:
            field = opts.get_ancestor_link(parent_opts.model)
            parent_field_chain.append(field)
            opts = field.remote_field.model._meta
        parent_field_chain.reverse()
        for field in parent_field_chain:
            path.extend(field.remote_field.get_path_info())
        return path

    def get_path_info(self, filtered_relation=None):
        opts = self.remote_field.model._meta
        object_id_field = opts.get_field(self.object_id_field_name)
        if object_id_field.model != opts.model:
            return self._get_path_info_with_parent()
        else:
            target = opts.pk
            pathinfo_data = dict(
                from_opts=self.model._meta,
                to_opts=opts,
                target_fields=(target,),
                join_field=self.remote_field,
                m2m=True,
                direct=False,
            )
            if DJANGO_GTE_20:
                pathinfo_data.update(dict(
                    filtered_relation=filtered_relation,
                ))
            return [PathInfo(**pathinfo_data)]

    def get_reverse_path_info(self, filtered_relation=None):
        opts = self.model._meta
        from_opts = self.remote_field.model._meta
        pathinfo_data = dict(
            from_opts=from_opts,
            to_opts=opts,
            target_fields=(opts.pk,),
            join_field=self,
            m2m=not self.unique,
            direct=False,
        )
        if DJANGO_GTE_20:
            pathinfo_data.update(dict(
                filtered_relation=filtered_relation,
            ))
        return [PathInfo(**pathinfo_data)]

    def value_to_string(self, obj):
        qs = getattr(obj, self.name).all()
        return force_text([instance._get_pk_val() for instance in qs])

    def contribute_to_class(self, cls, name, **kwargs):
        kwargs['private_only'] = True
        super().contribute_to_class(cls, name, **kwargs)
        self.model = cls
        setattr(cls, self.name, ReverseGenericOneToOneDescriptor(self.remote_field))

        # Add get_RELATED_order() and set_RELATED_order() to the model this
        # field belongs to, if the model on the other end of this relation
        # is ordered with respect to its corresponding GenericForeignKey.
        if not cls._meta.abstract:

            def make_generic_foreign_order_accessors(related_model, model):
                if self._is_matching_generic_foreign_key(model._meta.order_with_respect_to):
                    make_foreign_order_accessors(model, related_model)

            lazy_related_operation(make_generic_foreign_order_accessors, self.model, self.remote_field.model)

    def set_attributes_from_rel(self):
        pass

    def get_internal_type(self):
        return "ManyToManyField"

    def get_content_type(self):
        """
        Return the content type associated with this field's model.
        """
        return ContentType.objects.get_for_model(self.model,
                                                 for_concrete_model=self.for_concrete_model)

    def get_extra_restriction(self, where_class, alias, remote_alias):
        field = self.remote_field.model._meta.get_field(self.content_type_field_name)
        contenttype_pk = self.get_content_type().pk
        cond = where_class()
        lookup = field.get_lookup('exact')(field.get_col(remote_alias), contenttype_pk)
        cond.add(lookup, 'AND')
        return cond

    def bulk_related_objects(self, objs, using=DEFAULT_DB_ALIAS):
        """
        Return all objects related to ``objs`` via this ``GenericRelation``.
        """
        return self.remote_field.model._base_manager.db_manager(using).filter(**{
            "%s__pk" % self.content_type_field_name: ContentType.objects.db_manager(using).get_for_model(
                self.model, for_concrete_model=self.for_concrete_model).pk,
            "%s__in" % self.object_id_field_name: [obj.pk for obj in objs]
        })
