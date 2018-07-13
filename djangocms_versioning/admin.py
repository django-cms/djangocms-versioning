# from .models import BaseVersion
from django.apps import apps



class VersioningAdminMixin:
    """Mixin providing versioning functionality to admin classes.
    """
    # @TODO Implement versioning admin features here
    def save_model(self, request, obj, form, change):
        """
        Overrides the save method to create a version model
        when a content model is created
        """
        super().save_model(self, request, obj, form, change)
        if not change:
            # create a new version object
            extension = apps.get_app_config('djangocms_versioning').cms_extension
            new_version_model = extension.content_to_version_models[obj.__class__]
            #new_version_model = BaseVersion()
            #obj.
            # copy the content_id field to map to the content model
            # point it to the content object that is created
            # new_version_model.content_id = self.###


            # save the version model
            new_version_model.save()



