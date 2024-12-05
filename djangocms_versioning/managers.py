import warnings
from copy import copy

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q
from django.utils import timezone

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
        now = timezone.now()
        return queryset.filter(
            Q(versions__visibility_start=None) | Q(versions__visibility_start__lt=now),
            Q(versions__visibility_end=None) | Q(versions__visibility_end__gt=now),
            versions__state=PUBLISHED,
        )

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


class AdminQuerySetMixin:
    def _chain(self):
        # Also clone group by key when chaining querysets!
        clone = super()._chain()
        clone._group_by_key = self._group_by_key
        return clone

    def current_content(self, **kwargs):
        """Returns a queryset current content versions. Current versions are either draft
        versions or published versions (in that order). This optimized query assumes that
        draft versions always have a higher pk than any other version type. This is true as long as
        no other version type can be converted to draft without creating a new version."""
        pk_filter = self.filter(versions__state__in=(constants.DRAFT, constants.PUBLISHED))\
            .values(*self._group_by_key)\
            .annotate(vers_pk=models.Max("versions__pk"))\
            .values("vers_pk")
        return self.filter(versions__pk__in=pk_filter, **kwargs)

    def latest_content(self, **kwargs):
        """Returns the "latest" content object which is in this order
           1. a draft version (should it exist)
           2. a published version (should it exist)
           3. any other version with the highest pk

        This filter assumes that there can only be one draft created and that the draft as
        the highest pk of all versions (should it exist).
        """
        current = self.filter(versions__state__in=(constants.DRAFT, constants.PUBLISHED))\
            .values(*self._group_by_key)\
            .annotate(vers_pk=models.Max("versions__pk"))
        pk_current = current.values("vers_pk")
        pk_other = self.exclude(**{key + "__in": current.values(key) for key in self._group_by_key})\
            .values(*self._group_by_key)\
            .annotate(vers_pk=models.Max("versions__pk"))\
            .values("vers_pk")
        return self.filter(versions__pk__in=pk_current | pk_other, **kwargs)


class AdminManagerMixin:
    versioning_enabled = True
    _group_by_key = []

    def get_queryset(self):
        qs_class = super().get_queryset().__class__
        if not self._group_by_key:
            # Not initialized (e.g. by using content_set(manager="admin_manager"))?
            # Get grouping fields from versionable
            from . import versionables
            versionable = versionables.for_content(self.model)
            self._group_by_key = list(versionable.grouping_fields)
        qs = type(
            f"Admin{qs_class.__name__}",
            (AdminQuerySetMixin, qs_class),
            {"_group_by_key": self._group_by_key}  # Pass grouping fields to queryset
        )(self.model, using=self._db)
        return qs

    def current_content(self, **kwargs):  # pragma: no cover
        """Syntactic sugar: admin_manager.current_content()"""
        return self.get_queryset().current_content(**kwargs)

    def latest_content(self, **kwargs):  # pragma: no cover
        """Syntactic sugar: admin_manager.latest_content()"""
        return self.get_queryset().latest_content(**kwargs)
