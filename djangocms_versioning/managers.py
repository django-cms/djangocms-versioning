from .constants import PUBLISHED


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
