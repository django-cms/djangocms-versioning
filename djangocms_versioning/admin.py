from django.apps import apps


class VersioningAdminMixin:
    """Mixin providing versioning functionality to admin classes.
    """

    def save_model(self, request, obj, form, change):
        """
        Overrides the save method to create a version model
        when a content object is created
        """
        super().save_model(request, obj, form, change)
        if not change:
            # create a new version object and save it
            extension = apps.get_app_config('djangocms_versioning').cms_extension
            version_model = extension.content_to_version_models[obj.__class__]
            version_model.objects.create(content=obj)

    def get_queryset(self, request):
        """Limit query to most recent content versions
        """
        queryset = super().get_queryset(request)
        versioning_extension = apps.get_app_config(
            'djangocms_versioning').cms_extension
        version_model = versioning_extension.content_to_version_models[
            queryset.model]
        filter_name = '{}__in'.format(version_model.__name__.lower())
        latest_versions = version_model.objects.distinct_groupers()
        return queryset.filter(**{filter_name: latest_versions})

