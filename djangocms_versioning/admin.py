from django.db.models import Max


class VersioningAdminMixin:
    """Mixin providing versioning functionality to admin classes.
    """

    def get_queryset(self, request):
        """Limit query to most recent content versions
        """
        queryset = super(VersioningAdminMixin, self).get_queryset(request)
        query_str = """SELECT MAX(created), * FROM polls_pollcontent LEFT OUTER JOIN "polls_pollversion" ON ("polls_pollcontent"."id" = "polls_pollversion"."content_id") GROUP BY poll_id"""
        #~ return queryset.values('poll').annotate(Max('pollversion__created'))
        return queryset.raw(query_str)
