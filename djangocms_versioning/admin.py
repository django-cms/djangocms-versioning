from django.db.models import Max, Prefetch


class VersioningAdminMixin:
    """Mixin providing versioning functionality to admin classes.
    """

    def get_queryset(self, request):
        """Limit query to most recent content versions
        """
        queryset = super(VersioningAdminMixin, self).get_queryset(request)
        query_str = """SELECT MAX(created), polls_pollcontent.id FROM polls_pollcontent LEFT OUTER JOIN "polls_pollversion" ON ("polls_pollcontent"."id" = "polls_pollversion"."content_id") GROUP BY poll_id"""
        latest_version_ids = [record.id for record in queryset.raw(query_str)]
        return queryset.filter(id__in=latest_version_ids)
