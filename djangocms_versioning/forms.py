from functools import lru_cache

from django import forms

from . import versionables


class VersionContentChoiceField(forms.ModelChoiceField):

    def __init__(self, *args, **kwargs):
        self.language = kwargs.pop('language')
        self.predefined_label_method = kwargs.pop('option_label_override')
        super().__init__(*args, **kwargs)

    def label_from_instance(self, obj):
        if self.predefined_label_method:
            return self.predefined_label_method(obj, self.language)
        else:
            return super().label_from_instance(obj)


class GrouperFormMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        versionable = versionables.for_content(self._content_model)
        queryset = versionable.grouper_choices_queryset()
        self.fields[versionable.grouper_field_name].queryset = queryset


@lru_cache()
def grouper_form_factory(content_model, language=None):
    """Returns a form class used for selecting a grouper to see versions of.
    Form has a single field - grouper - which is a model choice field
    with available grouper objects for specified content model.

    :param content_model: Content model class
    """
    versionable = versionables.for_content(content_model)
    return type(
        content_model.__name__ + 'GrouperForm',
        (GrouperFormMixin, forms.Form,),
        {
            '_content_model': content_model,
            versionable.grouper_field_name: VersionContentChoiceField(
                queryset=versionable.grouper_model.objects.all(),
                label=versionable.grouper_model._meta.verbose_name,
                option_label_override=versionable.grouper_selector_option_label,
                language=language,
            )
        }
    )
