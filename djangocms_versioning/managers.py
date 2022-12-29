import warnings
from copy import copy
from itertools import groupby

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
        qs = self.filter(versions__state__in=("draft", "published"))\
            .order_by(*self._group_by_key)\
            .prefetch_related("versions")
        for grp, version_content in groupby(
            qs,
            lambda x: tuple(map(lambda key: getattr(x, key), self._group_by_key))  # get group key fields
        ):
            first, second = next(version_content), next(version_content, None)  # Max 2 results per group possible
            yield first if second is None or first.versions.first().state == constants.DRAFT else second


class AdminManagerMixin:
    versioning_enabled = True
    _group_by_key = []

    def get_queryset(self):
        qs = AdminQuerySet(self.model, using=self._db)
        qs._group_by_key = self._group_by_key
        return qs
