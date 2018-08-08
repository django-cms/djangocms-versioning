from functools import lru_cache

from django import forms
from django.apps import apps


@lru_cache()
def grouper_form_factory(content_model):
    """Returns a form class used for selecting a grouper to see versions of.
    Form has a single field - grouper - which is a model choice field
    with available grouper objects for specified content model.

    :param content_model: Content model class
    """
    versioning_extension = apps.get_app_config('djangocms_versioning').cms_extension
    versionable = versioning_extension.versionables_by_content[content_model]
    return type(
        versionable.grouper_model.__name__ + 'GrouperForm',
        (forms.Form,),
        {
            'grouper': forms.ModelChoiceField(
                queryset=versionable.grouper_model.objects.all(),
                label=versionable.grouper_model._meta.verbose_name,
            )
        }
    )
