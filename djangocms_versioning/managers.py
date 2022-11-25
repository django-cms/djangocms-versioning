import warnings
from copy import copy

from django.contrib.auth import get_user_model

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
            raise TypeError(f"User for with_user must be of type {get_user_model().__name__}")
        new_manager = copy(self)
        new_manager._user = user
        return new_manager
