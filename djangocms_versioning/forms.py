from functools import lru_cache

from django import forms

from . import versionables


class VersionContentChoiceField(forms.ModelChoiceField):
    """Form field used to display a list of grouper instances"""

    def __init__(self, *args, **kwargs):
        self.language = kwargs.pop("language")
        self.predefined_label_method = kwargs.pop("option_label_override")
        super().__init__(*args, **kwargs)

    def label_from_instance(self, obj):
        """Overridden to allow customizing the labels of the groupers"""
        if self.predefined_label_method:
            return self.predefined_label_method(obj, self.language)
        else:
            return super().label_from_instance(obj)


@lru_cache
def grouper_form_factory(content_model, language=None):
    """Returns a form class used for selecting a grouper to see versions of.
    Form has a single field - grouper - which is a model choice field
    with available grouper objects for specified content model.

    :param content_model: Content model class
    :param language: Language
    """
    versionable = versionables.for_content(content_model)
    valid_grouper_pk = content_model.admin_manager\
        .latest_content()\
        .values_list(versionable.grouper_field_name, flat=True)

    return type(
        content_model.__name__ + "GrouperForm",
        (forms.Form,),
        {
            "_content_model": content_model,
            versionable.grouper_field_name: VersionContentChoiceField(
                queryset=versionable.grouper_model.objects.filter(
                    pk__in=valid_grouper_pk,
                ),
                label=versionable.grouper_model._meta.verbose_name,
                option_label_override=versionable.grouper_selector_option_label,
                language=language,
            ),
        },
    )
