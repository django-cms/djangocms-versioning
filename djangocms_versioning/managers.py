from .constants import PUBLISHED


class PublishedContentManagerMixin:

    def get_queryset(self):
        """Limit query to published content
        """
        return super().get_queryset().filter(versions__state=PUBLISHED)
