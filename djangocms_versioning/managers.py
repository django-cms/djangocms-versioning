import warnings
from copy import copy

from django.contrib.auth import get_user_model
from django.db import models

from . import constants
from .constants import PUBLISHED
from .models import Version


class PublishedContentManagerMixin:
    """Manager mixin used for overriding the managers of content models"""
    versioning_enabled = True

    def get_queryset(self):
        """Limit query to published content
        """
        queryset = super().get_queryset()
        if not self.versioning_enabled:
            return queryset
        return queryset.filter(versions__state=PUBLISHED)

    def create(self, *args, **kwargs):
        obj = super().create(*args, **kwargs)
        created_by = kwargs.get("created_by", None)
        if not isinstance(created_by, get_user_model()):
            created_by = getattr(self, "_user", None)
        if created_by:
            Version.objects.create(content=obj, created_by=created_by)
        else:
            warnings.warn(
                f"No user has been supplied when creating a new {obj.__class__.__name__} object. "
                f"No version could be created. Make sure that the creating code also creates a "
                f"Version objects or use {obj.__class__.__name__}.objects.with_user(user).create(...)",
                UserWarning, stacklevel=2,
            )
        return obj

    def with_user(self, user):
        if not isinstance(user, get_user_model()) and user is not None:
            import inspect

            curframe = inspect.currentframe()
            callframe = inspect.getouterframes(curframe, 2)
            calling_function = callframe[1][3]
            raise ValueError(
                    f"With versioning enabled, {calling_function} requires a {get_user_model().__name__} instance "
                    f"to be passed as created_by argument"
                )
        new_manager = copy(self)
        new_manager._user = user
        return new_manager


class AdminQuerySet(models.QuerySet):
    def _chain(self):
        # Also clone group by key when chaining querysets!
        clone = super()._chain()
        clone._group_by_key = self._group_by_key
        return clone

    def current_content_iterator(self, **kwargs):
        """Returns generator (not a queryset) over current content versions. Current versions are either draft
        versions or published versions (in that order)"""
        warnings.warn("current_content_iterator is deprecated in favour of current_conent",
                      DeprecationWarning, stacklevel=2)
        return iter(self.current_content(**kwargs))

    def current_content(self, **kwargs):
        """Returns a queryset current content versions. Current versions are either draft
        versions or published versions (in that order). This optimized query assumes that
        draft versions always have a higher pk than any other version type. This is true as long as
        no other version type can be converted to draft without creating a new version."""
        qs = self.filter(versions__state__in=(constants.DRAFT, constants.PUBLISHED), **kwargs)
        pk_filter = qs.values(*self._group_by_key)\
            .annotate(vers_pk=models.Max("versions__pk"))\
            .values_list("vers_pk", flat=True)
        return qs.filter(versions__pk__in=pk_filter)


class AdminManagerMixin:
    versioning_enabled = True
    _group_by_key = []

    def get_queryset(self):
        qs = AdminQuerySet(self.model, using=self._db)
        qs._group_by_key = self._group_by_key
        return qs
