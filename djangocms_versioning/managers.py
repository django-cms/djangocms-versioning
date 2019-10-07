from django.db import models
from django.db.models.sql.where import WhereNode

from .constants import PUBLISHED


class PublishedQuerySet(models.QuerySet):

    def get(self, *args, **kwargs):
        """
        A get query should always be able to access entries which are not in
        a published state.
        """
        where_children = self.query.where.children
        all_except_published = [
            lookup for lookup in where_children
            if not (
                lookup.lookup_name == 'exact' and
                lookup.rhs == 'published' and
                lookup.lhs.field.name == 'state'
            )
        ]

        self.query.where = WhereNode()
        self.query.where.children = all_except_published
        return super().get(*args, **kwargs)


class PublishedContentManagerMixin:
    """Manager mixin used for overriding the managers of content models"""
    versioning_enabled = True

    def get_queryset(self):
        """Limit query to published content
        """
        queryset = PublishedQuerySet(self.model, using=self._db)
        if not self.versioning_enabled:
            return queryset
        return queryset.filter(versions__state=PUBLISHED)
