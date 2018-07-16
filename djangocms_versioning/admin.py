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
            version = version_model.objects.create(content=obj)
            version.save()
